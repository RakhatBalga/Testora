from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, tests, results, writing, speaking, analytics

app = FastAPI(title="Testora API")

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return {"message": "Welcome to Testora"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
