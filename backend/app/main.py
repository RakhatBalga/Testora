import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.infrastructure.config import settings
from app.infrastructure.logging import configure_logging
from app.infrastructure.errortracking import init_error_tracking
from app.infrastructure.database import SessionLocal, engine
from app.api.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.application.quota import reconcile_stale_reservations
from app.application.speaking import reconcile_stale_speaking
from app.application.writing import reconcile_stale_writing
from app.infrastructure.ai.factory import effective_provider
from app.infrastructure.ai.qwen import ping_qwen
from app.infrastructure.time import utcnow
from app.api.routers import auth, tests, results, writing, speaking, analytics, learning, listening
from app.api.routers import history, vocabulary

configure_logging()
init_error_tracking()
logger = logging.getLogger("testora")


def _validate_security_configuration() -> None:
    """In production, refuse to start on a missing/placeholder/weak SECRET_KEY.

    Config only requires SECRET_KEY to be *present* — it would happily accept the
    ".env.example" placeholder or a short, guessable value, which would make every
    issued JWT trivially forgeable. Fail fast instead. Dev/staging are unaffected.
    """
    if not settings.is_production:
        return
    key = (settings.SECRET_KEY or "").strip()
    # Placeholders plus values known to have leaked in this repo's git history
    # (an early commit tracked backend/.env). A leaked key is forever burned —
    # reject it regardless of length so it can never be reused in production.
    placeholders = {
        "",
        "change_me",
        "changeme",
        "secret",
        "your-secret-key",
        "mysecretkey123",  # leaked in git history — permanently unusable
    }
    if key.lower() in placeholders or len(key) < 32:
        raise RuntimeError(
            "Refusing to start in production with a missing/placeholder/weak/"
            "leaked SECRET_KEY (need >=32 chars, not a placeholder or a value "
            "leaked in git history). Generate one with `openssl rand -hex 32`."
        )


def _validate_ai_configuration() -> None:
    """Guard against shipping the free mock grader to production.

    The grader factory silently falls back to the mock when a real provider is
    selected without its API key. In production that would mean every user gets
    fake grades (and Band-0 Speaking) — so we refuse to start. Outside
    production we only warn, keeping local/dev mock grading frictionless.
    """
    provider = effective_provider()
    if settings.is_production and provider == "mock":
        raise RuntimeError(
            "Refusing to start in production with the mock grader. Set "
            "AI_PROVIDER=gemini and provide GEMINI_API_KEY, or set AI_PROVIDER=qwen "
            f"with QWEN_BASE_URL and QWEN_MODEL (current AI_PROVIDER={settings.AI_PROVIDER!r})."
        )
    if provider == "mock" and settings.AI_PROVIDER.lower() != "mock":
        logger.warning(
            "AI_PROVIDER=%s but its API key is empty — falling back to the free "
            "mock grader (Speaking returns Band 0). Real grading is DISABLED.",
            settings.AI_PROVIDER,
        )
    else:
        logger.info("AI grading provider: %s", provider)


def _reconcile_on_startup() -> None:
    """A killed worker leaves gradings pending and reservations charged: undo both."""
    try:
        with SessionLocal() as db:
            writing = reconcile_stale_writing(db)
            reservations = reconcile_stale_reservations(db) + reconcile_stale_speaking(db)
        if writing or reservations:
            logger.warning(
                "Startup reconciliation: %s stale writing submission(s) marked failed, "
                "%s stale AI reservation(s) released",
                writing,
                reservations,
            )
    except Exception:  # noqa: BLE001 - a DB blip must not stop the app from booting
        logger.exception("Startup reconciliation failed; it will run lazily per user instead")


# How long after boot the previous process may still be finishing requests: on a
# deploy Render starts the new instance first, then stops the old one (SIGTERM,
# killed 30 s later). Gradings that began before this boot are orphans after that.
ORPHAN_SWEEP_DELAY_SECONDS = 120


def _reconcile_orphaned_gradings(booted_at: datetime) -> int:
    """Fail every writing grading that was started before this process booted.

    Grading runs synchronously inside its request, so a row that is still
    pending from before the boot has no request left to finish it. Without this
    it would stay "pending" (unretryable, and blocking a resubmit) until the
    stale window passes. Assumes one API process, as start-render.sh and the
    Dockerfile run it: with several workers a sibling's live grading would
    match, so this sweep must go if the app is ever started with --workers.
    """
    try:
        with SessionLocal() as db:
            orphans = reconcile_stale_writing(db, started_before=booted_at)
        if orphans:
            logger.warning(
                "Startup reconciliation: %s grading(s) orphaned by the previous process marked failed", orphans
            )
        return orphans
    except Exception:  # noqa: BLE001 - the stale-window sweep still covers these rows
        logger.exception("Orphaned grading reconciliation failed; the stale-window sweep will handle them")
        return 0


async def _sweep_orphans_after_handover(booted_at: datetime) -> None:
    await asyncio.sleep(ORPHAN_SWEEP_DELAY_SECONDS)
    await run_in_threadpool(_reconcile_orphaned_gradings, booted_at)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate configuration before serving any traffic; either guard raising
    # here aborts startup (fail fast) rather than degrading silently.
    _validate_security_configuration()
    _validate_ai_configuration()
    booted_at = utcnow()  # no request of this process can have started a grading earlier
    await run_in_threadpool(_reconcile_on_startup)
    orphan_sweep = asyncio.create_task(_sweep_orphans_after_handover(booted_at))
    try:
        yield
    finally:
        orphan_sweep.cancel()


app = FastAPI(
    title="Testora API",
    lifespan=lifespan,
    # Defense-in-depth: hide interactive docs / OpenAPI schema in production
    # (Caddy already 404s these paths; this removes them at the app layer too).
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
# Added after CORS so they wrap it: oversized bodies are rejected before any
# parsing, and every response (even CORS preflights) carries a request id.
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the real error with the request id; tell the user only that it failed."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    rid = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again.", "request_id": rid},
    )


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(tests.router, prefix="/tests", tags=["Tests"])
app.include_router(results.router, prefix="/results", tags=["Results"])
app.include_router(writing.router, prefix="/writing", tags=["Writing"])
app.include_router(speaking.router, prefix="/speaking", tags=["Speaking"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(history.router, prefix="/history", tags=["History"])
app.include_router(learning.router, prefix="/learning", tags=["Learning"])
app.include_router(listening.router, prefix="/listening", tags=["Listening"])
app.include_router(vocabulary.router, prefix="/vocabulary", tags=["Vocabulary"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return {"message": "Welcome to Testora"}


@app.get("/health")
def health_check():
    # Back-compat alias for the liveness probe.
    return {"status": "ok"}


@app.get("/health/live")
async def health_live():
    """Liveness: the process is up and the event loop is responsive."""
    return {"status": "alive"}


def _check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — readiness must never raise
        logger.exception("Readiness DB check failed")
        return False


@app.get("/health/ready")
async def health_ready(response: Response):
    """Readiness: only route traffic here once dependencies are usable.

    Verifies the database is reachable and reports the effective grader. The DB
    check runs in the threadpool so it can't block the event loop.
    """
    db_ok = await run_in_threadpool(_check_db)
    provider = effective_provider()
    grading_ok = not (settings.is_production and provider == "mock")
    result = {"grading_provider": provider}
    if provider == "qwen":
        # The self-hosted model server can be down while the API itself is fine.
        qwen = await ping_qwen()
        result["qwen"] = qwen
        grading_ok = grading_ok and qwen["ok"] and qwen["model_available"]
    ready = db_ok and grading_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "down",
        **result,
    }
