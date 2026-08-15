FROM python:3.11-slim

# psycopg/asyncpg and cryptography need build essentials + libpq at build time;
# curl is handy for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as a non-root user by convention —
# UID 1000 with a writable $HOME, since the model cache (~/.cache/huggingface)
# and our own generated CA bundle (./certs) both need to be written at runtime.
RUN useradd -m -u 1000 appuser
WORKDIR /app

COPY --chown=appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser . .

USER appuser
ENV HOME=/home/appuser

# Hugging Face Spaces (Docker SDK) expects the app to listen on 7860 and
# routes external traffic there regardless of what's in the README's
# app_port — keep both in sync if you ever change this.
ENV PORT=7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Run the pending Alembic migrations, then start the API.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
