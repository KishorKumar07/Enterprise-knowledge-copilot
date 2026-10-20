FROM python:3.11-slim

# psycopg/asyncpg and cryptography need build essentials + libpq at build time;
# curl is handy for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional extra root CA for local builds on a network that re-signs HTTPS
# (e.g. Avast Web Shield), which otherwise breaks pip and the Hugging Face
# download with CERTIFICATE_VERIFY_FAILED. Drop a .crt into backend/.local-ca/
# (gitignored). With no .crt there — CI, the server — update-ca-certificates is
# a no-op and TLS stays strict.
COPY .local-ca /usr/local/share/ca-certificates/local
RUN update-ca-certificates
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt     REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt     PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# Hugging Face Spaces runs containers as a non-root user by convention —
# UID 1000 with a writable $HOME, since the model cache (~/.cache/huggingface)
# and our own generated CA bundle (./certs) both need to be written at runtime.
RUN useradd -m -u 1000 appuser
WORKDIR /app

COPY --chown=appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the two local models (app/rag/embeddings.py and app/rag/reranker.py)
# so the weights live in an image layer. These run on-device via
# sentence-transformers — only the chat LLM (Gemini/Groq) is a remote API — so
# without this the first user request fetches ~220 MB from Hugging Face while
# someone waits on it, and times out.
#
# Kept above `COPY . .` so editing application code doesn't invalidate this
# (slow) layer. HF_HOME must be set here as well as at runtime, or the download
# lands somewhere the appuser can't read it back from.
ENV HF_HOME=/home/appuser/.cache/huggingface
RUN mkdir -p $HF_HOME && chown -R appuser:appuser /home/appuser/.cache
USER appuser
RUN python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
USER root

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

# Migrations are deliberately NOT run here. This used to be
# `alembic upgrade head && uvicorn ...`, which re-runs on every restart and,
# with more than one container, runs Alembic concurrently against one database.
# It also turns a failed migration into a crash-looping container instead of a
# clear failed deploy step. The deploy runs `alembic upgrade head` as its own
# step before starting the new container.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
