from fastapi import FastAPI
from app.routers import auth

app = FastAPI()

app.include_router(auth.router, pregix="/auth", tags=["Auth"])

@app.get("/")
def root():
    return {"message": "Welcome to Testora"}

@app.get("/health")
def health_check():
    return {"status": "ok"}