from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Deployment environment: "development" | "staging" | "production".
    # In production the app refuses to start on the free mock grader.
    APP_ENV: str = "development"

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # 24h: long enough that a token never expires mid-session (a Writing task is
    # allotted 40 min) while still bounding exposure of a leaked token.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Comma-separated list of allowed browser origins. Defaults to local dev;
    # MUST be set in production, e.g. "https://testora.studio,https://www.testora.studio".
    CORS_ORIGINS: str = "http://localhost:3000"

    # IANA timezone used for day-boundary logic (streaks, "today's plan").
    # Users are in CIS/MENA, so UTC would shift day boundaries by several hours.
    APP_TIMEZONE: str = "Asia/Almaty"

    # Upload / input ceilings (defence against memory blowup, cost, and DoS).
    MAX_AUDIO_UPLOAD_MB: int = 15
    MAX_WRITING_CHARS: int = 20000

    # Max grading calls running concurrently. Bounds threadpool usage (so slow
    # AI calls can't starve fast endpoints) and concurrent Gemini calls (cost /
    # quota protection). Excess requests queue rather than pile onto the model.
    MAX_CONCURRENT_GRADINGS: int = 8

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"

    # Optional error tracking. When set (and sentry-sdk is installed), unhandled
    # exceptions are reported. Empty = disabled (default), so dev is unaffected.
    SENTRY_DSN: str = ""

    AI_PROVIDER: str = "mock"  # mock | claude | gemini
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Run the second-stage Writing "coach" call (personalised guidance + roadmap).
    # Disable to halve Writing grading cost/latency (examiner scores still return).
    WRITING_COACH_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()