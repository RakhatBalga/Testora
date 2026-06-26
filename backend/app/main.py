import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.infrastructure.config import settings
from app.infrastructure.logging import configure_logging
from app.infrastructure.errortracking import init_error_tracking
from app.infrastructure.database import engine
from app.infrastructure.ai.factory import effective_provider
from app.api.routers import auth, tests, results, writing, speaking, analytics
from app.api.routers import history

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
    placeholders = {"", "change_me", "changeme", "secret", "your-secret-key"}
    if key.lower() in placeholders or len(key) < 32:
        raise RuntimeError(
            "Refusing to start in production with a missing/placeholder/weak "
            "SECRET_KEY (need >=32 chars, not a placeholder). Generate one with "
            "`openssl rand -hex 32`."
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
            "AI_PROVIDER=gemini and provide GEMINI_API_KEY (current "
            f"AI_PROVIDER={settings.AI_PROVIDER!r})."
        )
    if provider == "mock" and settings.AI_PROVIDER.lower() != "mock":
        logger.warning(
            "AI_PROVIDER=%s but its API key is empty — falling back to the free "
            "mock grader (Speaking returns Band 0). Real grading is DISABLED.",
            settings.AI_PROVIDER,
        )
    else:
        logger.info("AI grading provider: %s", provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate configuration before serving any traffic; either guard raising
    # here aborts startup (fail fast) rather than degrading silently.
    _validate_security_configuration()
    _validate_ai_configuration()
    yield


app = FastAPI(title="Testora API", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(tests.router, prefix="/tests", tags=["Tests"])
app.include_router(results.router, prefix="/results", tags=["Results"])
app.include_router(writing.router, prefix="/writing", tags=["Writing"])
app.include_router(speaking.router, prefix="/speaking", tags=["Speaking"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(history.router, prefix="/history", tags=["History"])
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
    ready = db_ok and grading_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "down",
        "grading_provider": provider,
    }
