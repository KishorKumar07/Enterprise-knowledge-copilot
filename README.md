# Enterprise Knowledge Copilot

A full-stack AI assistant that connects to a company's Google Drive and Slack, indexes selected content with a hybrid RAG pipeline, and answers employee questions through a multi-agent LangGraph workflow — every answer grounded with real, clickable citations.

## Highlights

- **OAuth-only onboarding** for Google Drive and Slack — pick specific folders/channels to index, with live sync progress
- **Hybrid RAG**: pgvector similarity + Postgres full-text search, fused and reranked, not naive vector search
- **Multi-agent pipeline (LangGraph)**: Supervisor → Retrieval → Research → Answer/Citation
- **Streaming chat** with markdown, expandable source cards, regenerate/stop/feedback, conversation history
- **Gemini + Groq fallback** behind a single swappable LLM layer
- **Security**: encrypted OAuth tokens, per-org data isolation, rate limiting, prompt-injection–hardened retrieval
- **Polished UI**: dark mode, fully responsive, Framer Motion micro-interactions
- **Agent ops**: every LangGraph node emits an OpenTelemetry span, a Prometheus metric, and a Postgres audit row — self-hosted, free, no vendor accounts

## Stack

**Frontend**: Next.js 16, TypeScript, Tailwind, shadcn/ui, Framer Motion
**Backend**: FastAPI, LangGraph, SQLAlchemy (async)
**Data/AI**: PostgreSQL + pgvector, sentence-transformers (embeddings + reranking), Gemini / Groq
**Agent ops**: OpenTelemetry (instrumentation) → Arize Phoenix (LLM trace waterfalls, token/cost) + Prometheus/Grafana (system metrics, dashboards, alerting) + Postgres `agent_runs`/`agent_steps` (durable per-turn audit trail)

## Live demo and deployment

**https://kishor-ekc.duckdns.org** — deployed to AWS (EC2, ECR, SSM) by GitHub Actions with OIDC, no stored
cloud credentials. See [DEPLOYMENT.md](DEPLOYMENT.md) for the architecture, the pipeline, what went wrong along
the way, and a Jenkins vs GitHub Actions comparison.

## Running locally

### Option A: everything in Docker (matches production)

```bash
cp backend/.env.docker.example backend/.env.docker   # add your API keys, JWT secret and Fernet key
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

App on http://localhost:3000, API on :7860, Grafana on :3001 (`admin` / `admin`), Phoenix on :6006.

### Option B: run the app on your machine, infrastructure in Docker

```bash
# Database only (add phoenix prometheus grafana for the observability stack; note that Prometheus
# scrapes the backend *container*, so Grafana charts stay empty when the backend runs on the host)
docker compose up -d postgres

# Backend
cd backend && python -m venv venv && ./venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install
cp .env.local.example .env.local
npm run dev
```

Needs `GEMINI_API_KEY`/`GROQ_API_KEY` for chat, and Google/Slack OAuth credentials for source connections — the app degrades gracefully without them rather than breaking.

## Agent ops

`docker compose up -d --build` (Option A above) also starts the observability stack:

- **Phoenix** — LLM trace waterfalls, prompts/completions, token usage: [http://localhost:6006](http://localhost:6006)
- **Grafana** — system/agent dashboards (pre-provisioned "EKC — Agent Ops" dashboard): [http://localhost:3001](http://localhost:3001)
- **Prometheus** — raw metrics/queries: [http://localhost:9090](http://localhost:9090)
- Backend `/metrics` — what Prometheus scrapes: [http://localhost:8000/metrics](http://localhost:8000/metrics)

Every LangGraph node run (`supervisor` → `retrieval` → `research` → `answer_agent`) produces three things simultaneously: an OpenTelemetry span sent to Phoenix, a Prometheus histogram/counter observation, and an `agent_steps` row in Postgres tied to an `agent_runs` row for that conversation turn — see `backend/app/agents/tracing.py`. LLM calls (Gemini/Groq) are auto-instrumented via OpenInference, so token counts and cost show up in Phoenix without any changes to `app/services/llm.py`.

Set `OTEL_ENABLED=false` in `backend/.env` to disable tracing entirely — exporter failures are non-fatal either way, so the app runs fine with the observability containers stopped.

**In-product view**: the "Agent Ops" page in the app (`/app/agent-ops`) reads the same `agent_runs`/`agent_steps` tables directly — recent runs, status, latency, and a per-run step breakdown, scoped to your organization, plus quick links out to Phoenix and Grafana.

**Quality gate**: `backend/tests/eval/` runs the real research/answer agents against fixed golden contexts and grades the output with an LLM judge (faithfulness + relevancy, RAGAS-style metrics computed by hand — RAGAS's current release forces a `langgraph>=1.2` upgrade that breaks the pinned `langgraph==0.2.62` used by the actual pipeline). Needs only `GEMINI_API_KEY`/`GROQ_API_KEY` — no database:

```bash
cd backend && pytest tests/eval -v
```

---

Portfolio project.
