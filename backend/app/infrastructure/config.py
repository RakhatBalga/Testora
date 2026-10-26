from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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

    # Comma-separated proxy IPs/CIDRs whose X-Forwarded-For may be trusted.
    # Empty = ignore X-Forwarded-For and rate-limit by the direct peer address.
    # The client IP is the right-most X-Forwarded-For hop that is NOT in this
    # list, so list every proxy hop between the internet and the app (on Render:
    # the private range of its load balancer, see the first-request INFO log).
    TRUSTED_PROXY_CIDRS: str = ""

    # IANA timezone used for day-boundary logic (streaks, "today's plan").
    # Users are in CIS/MENA, so UTC would shift day boundaries by several hours.
    APP_TIMEZONE: str = "Asia/Almaty"

    # Upload / input ceilings (defence against memory blowup, cost, and DoS).
    MAX_AUDIO_UPLOAD_MB: int = 15
    MAX_AVATAR_UPLOAD_MB: int = 5
    MAX_WRITING_CHARS: int = 20000
    # Hard cap for any non-upload request body, checked before parsing (the
    # audio/avatar routes get their own cap derived from the limits above).
    MAX_REQUEST_BODY_BYTES: int = 1024 * 1024

    # Database safety nets: fail fast instead of hanging a worker thread when
    # Neon is waking up or a query runs away.
    DB_CONNECT_TIMEOUT_SECONDS: int = 10
    DB_STATEMENT_TIMEOUT_MS: int = 30000
    DB_POOL_TIMEOUT_SECONDS: int = 15

    # Where uploaded blobs (avatars, speaking audio) live: "database" keeps them
    # in Postgres (survives Render restarts), "local" uses the disk (dev only).
    STORAGE_BACKEND: str = "database"
    # Speaking can be switched off server-side (the UI gate alone is bypassable).
    # FREE_SPEAKING_SUBMISSIONS=0 also disables it.
    SPEAKING_ENABLED: bool = True

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

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    AI_PROVIDER: str = "mock"  # mock | claude | gemini | qwen
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Cheaper/faster model for the secondary generative calls (coach guidance,
    # Better Version rewrite). Band accuracy lives in GEMINI_MODEL (examiner);
    # these calls only write prose, where flash quality is fine and each Pro
    # call would add 15-25s of latency and most of the per-submission cost.
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"

    # Locally hosted Qwen behind an OpenAI-compatible API (/v1/chat/completions).
    QWEN_BASE_URL: str = ""
    QWEN_MODEL: str = ""
    QWEN_API_KEY: str = ""
    QWEN_TIMEOUT_SECONDS: int = 120

    # Run the second-stage Writing "coach" call (personalised guidance + roadmap).
    # Disable to halve Writing grading cost/latency (examiner scores still return).
    WRITING_COACH_ENABLED: bool = True

    # Free-tier AI grading quotas (per account, lifetime, until subscriptions
    # exist). Failed gradings do not consume quota. 0 = feature disabled
    # entirely; negative = unlimited (dev).
    FREE_WRITING_SUBMISSIONS: int = 2
    FREE_SPEAKING_SUBMISSIONS: int = 2
    # Legacy setting accepted for deployment compatibility, but no longer grants access.
    QUOTA_EXEMPT_USERS: str = ""
    # Immutable IDs replace username exemptions; renaming cannot grant free AI.
    QUOTA_EXEMPT_USER_IDS: str = ""
    # Shared per-user daily budget (app timezone day) includes failed attempts
    # and vocabulary generation.
    AI_DAILY_ATTEMPTS: int = Field(default=20, ge=1)
    # Global daily budget across ALL users (AI reservations per app-timezone
    # day); protects the provider bill from scripted sign-ups. Negative = off.
    AI_GLOBAL_DAILY_ATTEMPTS: int = 400
    # A pending grading older than this is considered dead (worker killed) and
    # is reconciled: marked failed and its quota refunded. Must exceed the
    # slowest legitimate grading (3 x 60 s timeout, two stages).
    GRADING_STALE_MINUTES: int = Field(default=10, ge=1)
    # Max time a request waits for a free grading slot before getting a 503.
    GRADING_QUEUE_TIMEOUT_SECONDS: int = 30

    @property
    def quota_exempt_user_ids(self) -> set[int]:
        return {int(u.strip()) for u in self.QUOTA_EXEMPT_USER_IDS.split(",") if u.strip().isdigit()}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env")

    # --- Qwen (self-hosted, OpenAI-compatible API; AI_PROVIDER=qwen) ---------
    # Base URL including /v1, e.g. http://localhost:11434/v1 (Ollama) or
    # https://<gpu-host>/v1 (vLLM). Both URL and model are required for qwen.
    QWEN_BASE_URL: str = ""
    QWEN_MODEL: str = ""
    # Optional bearer token (vLLM --api-key, a reverse proxy). Empty = none.
    QWEN_API_KEY: str = ""
    # Local inference is slow (tens of seconds per essay on a laptop).
    QWEN_TIMEOUT_SECONDS: float = Field(default=180.0, gt=0)
    # Grading runs with Qwen3 "thinking" off: faster and stable JSON.
    QWEN_DISABLE_THINKING: bool = True


settings = Settings()
