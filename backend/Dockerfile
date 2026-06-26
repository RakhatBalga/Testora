FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 build are avoided by using psycopg2-binary.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" --uid 10001 testora

COPY --chown=testora:testora . .
RUN mkdir -p /app/private/audio_submissions /app/static && \
    chown -R testora:testora /app/private /app/static

USER testora

# Run migrations, then serve. Fail fast if migrations fail.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
