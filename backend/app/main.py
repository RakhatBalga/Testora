from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, tests, results

app = FastAPI(title="Testora API")

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


@app.get("/")
def root():
    return {"message": "Welcome to Testora"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
