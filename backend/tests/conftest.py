"""Test fixtures and environment.

Settings require DATABASE_URL/SECRET_KEY at import; set throwaway values before
the app package is imported so unit tests don't need a real database. The Gemini
tests never open a DB connection — they exercise the grading logic in isolation.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-for-anything-real")
os.environ.setdefault("AI_PROVIDER", "mock")
