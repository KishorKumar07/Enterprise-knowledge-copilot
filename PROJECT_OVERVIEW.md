# Enterprise Knowledge Copilot — Project Overview

A full-stack AI assistant that connects to a company's Google Drive and Slack, indexes selected content with a hybrid RAG pipeline, and answers employee questions through a multi-agent LangGraph workflow — every answer grounded with real, clickable citations.

## What it does

- **OAuth-only onboarding** for Google Drive and Slack — users pick specific folders/channels to index, with live sync progress.
- **Hybrid RAG retrieval**: pgvector similarity search + Postgres full-text search, fused and reranked (not naive vector-only search).
- **Multi-agent pipeline (LangGraph)**: `Supervisor → Retrieval → Research → Answer/Citation`.
- **Streaming chat UI**: markdown rendering, expandable source cards, regenerate/stop/feedback, conversation history.
- **LLM layer**: Gemini as primary with Groq fallback, behind a single swappable interface.
- **Security**: encrypted OAuth tokens, per-organization data isolation, rate limiting, prompt-injection–hardened retrieval.
- **Agent ops / observability**: every LangGraph node emits an OpenTelemetry span, a Prometheus metric, and a Postgres audit row — fully self-hosted, no vendor accounts required.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind, shadcn/ui, Framer Motion |
| Backend | FastAPI, LangGraph, SQLAlchemy (async) |
| Data / AI | PostgreSQL + pgvector, sentence-transformers (embeddings + reranking), Gemini / Groq |
| Agent ops | OpenTelemetry → Arize Phoenix (LLM trace waterfalls, token/cost) + Prometheus/Grafana (metrics, dashboards, alerting) + Postgres `agent_runs`/`agent_steps` (durable per-turn audit trail) |

## Repository layout

```
backend/
  app/
    agents/       # LangGraph nodes (supervisor, retrieval, research, answer) + tracing.py
    api/          # FastAPI routes
    auth/         # OAuth + session/auth logic
    connectors/   # Google Drive / Slack integrations
    core/         # config, settings, shared infra
    ingestion/    # content sync & chunking pipeline
    mcp/          # MCP-related integration
    models/       # SQLAlchemy models
    rag/          # hybrid retrieval, reranking
    schemas/      # Pydantic schemas
    services/     # llm.py and other service-layer logic
    utils/, workers/
  alembic/        # DB migrations
  tests/          # incl. tests/eval — LLM-judge quality gate

frontend/
  src/
    app/          # Next.js app router: chat, sources, settings, profile, agent-ops, onboarding, login/signup
    components/   # chat, dashboard, layout, onboarding, sources, ui
    hooks/, lib/, services/, types/

observability/
  grafana/, prometheus.yml   # pre-provisioned "EKC — Agent Ops" dashboard

sample-drive-content/        # sample docs used for demoing ingestion
docker-compose.yml           # Postgres + Phoenix + Prometheus + Grafana
```

## Running locally

```bash
# Database + observability stack
docker compose up -d

# Backend
cd backend && python -m venv venv && ./venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # add API keys
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install
cp .env.local.example .env.local
npm run dev
```

Requires `GEMINI_API_KEY` / `GROQ_API_KEY` for chat, and Google/Slack OAuth credentials for source connections. The app degrades gracefully without them rather than breaking.

## Observability endpoints

- Phoenix (LLM trace waterfalls): http://localhost:6006
- Grafana (dashboards): http://localhost:3001
- Prometheus (raw metrics): http://localhost:9090
- Backend `/metrics`: http://localhost:8000/metrics
- In-app "Agent Ops" page (`/app/agent-ops`): reads `agent_runs`/`agent_steps` directly, scoped per organization, with links out to Phoenix/Grafana

Set `OTEL_ENABLED=false` in `backend/.env` to disable tracing; exporter failures are non-fatal either way.

## Quality gate

`backend/tests/eval/` runs the real research/answer agents against fixed golden contexts and grades output with an LLM judge (faithfulness + relevancy, RAGAS-style metrics computed by hand, since RAGAS's current release requires a `langgraph` upgrade incompatible with the pinned `langgraph==0.2.62`). Needs only `GEMINI_API_KEY`/`GROQ_API_KEY`, no database:

```bash
cd backend && pytest tests/eval -v
```

## Development history (git log)

1. **Initial commit** — Enterprise Knowledge Copilot scaffolding (backend, frontend, observability, docker-compose).
2. **chore: remove obsolete test utility files** — cleanup.
3. **Fix alembic to read `DATABASE_URL` directly** instead of via configparser.
4. **Feat: agent ops added** — OpenTelemetry/Phoenix/Prometheus/Grafana tracing pipeline, `agent_runs`/`agent_steps` audit tables, and the in-app Agent Ops page.

---
*Generated from repository state as of 2026-08-23. This is a portfolio project.*
