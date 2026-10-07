# AWS Deployment Plan — Enterprise Knowledge Copilot (GitHub Actions CI/CD)

> **Project 2 of 2.** Deploy this one **second**.
> Sister plan: `System-Design-Studio/AWS-DEPLOYMENT-PLAN.md` — **do that one first.** It builds the AWS account, app server, Postgres, Nginx, TLS, and ECR patterns that this plan reuses.
>
> **Status:** Blocked on the sister plan — update the Progress Tracker (Section 10).
> **Owner:** Kishor (kishorr21cse@gmail.com) · **Created:** 2026-09-29 · **Facts verified:** 2026-09-29

---

## 0. How to use this document

Self-contained execution plan for **this** project. Written after a full codebase analysis — **you do not need to re-explore the repo to begin.** Section 1 has every fact you need.

**Rules for the executing agent:**

1. **Check the prerequisites (Section 2) before starting.** This plan assumes shared infrastructure already exists.
2. **Work phase by phase, in order.**
3. **Update the Progress Tracker** (Section 10) after each phase. Record blockers there.
4. **Verify before relying.** Accurate as of 2026-09-29. If a path or line number doesn't match, trust the repo and correct this doc.
5. **Never invent AWS costs or Free Tier rules.** Section 4 has verified numbers. Anything else — say you need to check.
6. **The user is an AWS beginner.** Explain *why*, not just *what*.
7. **All code here is a starting template, not verified output.** Build it, run it, fix what breaks. Don't claim it works until you've seen it work.
8. **Secrets never enter git** — not in Dockerfiles, compose files, or workflow YAML.
9. **Don't commit or push unless the user asks.**

**Also read:** `backend/README.md` (currently written for Hugging Face Spaces — **superseded by this plan**), root `README.md`.

**This is the harder of the two projects.** Three services instead of one, a 2 GB image, 24 environment variables, two OAuth consoles, SSE streaming, and cookie-based auth. That is exactly why it goes second.

---

## 1. Project facts

| Fact | Value |
|---|---|
| Repo | `github.com/KishorKumar07/Enterprise-knowledge-copilot`, branch **`main`** |
| Path | `E:\Kishor\Projects\Enterprise-knowledge-copilot` |
| Note | `System-Design-Studio/` is nested here but is a **separate git repo** |
| Commits | 4 |
| Backend | **Python 3.11, FastAPI 0.115.6**, async SQLAlchemy 2.0, LangGraph 0.2.62 |
| Entrypoint | `backend/app/main.py`, app object `app` |
| Agents | LangGraph supervisor → research → retrieval → answer (`backend/app/agents/`) |
| Frontend | Next.js 16.3.1, React 19.2.8, Tailwind v4 — **no Dockerfile exists** |
| Database | PostgreSQL 16 **+ pgvector** — `document_chunks.embedding VECTOR(384)`, HNSW cosine + GIN full-text |
| Migrations | **Alembic, 5 migrations**, head = `e64400b1d29d` |
| Embeddings | `BAAI/bge-small-en-v1.5` — **local PyTorch CPU**, ~130 MB, `backend/app/rag/embeddings.py` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` — local, ~90 MB, `backend/app/rag/reranker.py` |
| Model download | **At runtime on first query**, from HuggingFace Hub → **60s+ first-request hang** |
| LLM | Gemini (`google-genai`) primary, Groq (OpenAI-compatible) fallback — `backend/app/services/llm.py` |
| Connectors | Google Drive v3 + Slack, both OAuth (`backend/app/connectors/`) |
| Auth | Custom JWT in **httpOnly cookie** `ekc_session`, HS256, 7-day expiry, bcrypt (`backend/app/api/auth.py`) |
| Multi-tenancy | `organization_id` on every row, filtered on every query |
| Token storage | OAuth provider tokens **Fernet-encrypted at rest** (`backend/app/core/encryption.py`) |
| Streaming | **Server-Sent Events** on chat (`backend/app/services/chat_stream.py`) |
| Background work | **FastAPI `BackgroundTasks` in the web process** — no worker, no queue. `backend/app/workers/` is empty |
| Rate limiting | slowapi, **in-memory** (`backend/app/core/rate_limit.py`) |
| Tests | pytest, `backend/tests/` — **never run in CI** |
| CI today | **None** |
| Docker today | `backend/Dockerfile` only (Hugging Face Spaces shaped, `PORT=7860`) |
| Ports | backend 8000 (container default 7860), frontend 3000 |
| Image size | **~2 GB** (torch CPU + sentence-transformers) |
| RAM needed | **~1.5 GB** |

**Environment variables (24):**

`ENVIRONMENT`, `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `SESSION_COOKIE_NAME`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `CREDENTIAL_ENCRYPTION_KEY`, `FRONTEND_ORIGIN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_REDIRECT_URI`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_UTILITY_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_UTILITY_MODEL`, `OTEL_ENABLED`, `PHOENIX_ENDPOINT`

Defined in `backend/app/core/config.py` (pydantic-settings, case-insensitive, `env_file=".env"`). Template in `backend/.env.example`.

Frontend: **`NEXT_PUBLIC_API_URL` only** — used in `src/services/api-client.ts`, `chat.ts`, `server-auth.ts`, `sources.ts`, all defaulting to `http://localhost:8000`.

> ⚠️ `CREDENTIAL_ENCRYPTION_KEY` — **if this is lost, every stored Google/Slack OAuth token becomes permanently undecryptable.** Back it up somewhere safe.

**Issues this plan must fix:**

| # | Issue | Where |
|---|---|---|
| 1 | `next.config.ts` is an empty config — needs `output: "standalone"` | `frontend/next.config.ts` |
| 2 | **No frontend Dockerfile exists** | `frontend/` |
| 3 | Models download at runtime → 60s+ first-query hang | `backend/app/rag/` |
| 4 | Prometheus target `host.docker.internal:8000` is Windows-only, breaks on Linux | `observability/prometheus.yml` |
| 5 | Grafana/Phoenix URLs hardcoded to `localhost:3001` / `localhost:6006` | `frontend/src/app/app/agent-ops/page.tsx:14-15` |
| 6 | `alembic upgrade head` runs in the container `CMD` — races on restart | `backend/Dockerfile` |
| 7 | Backend Dockerfile defaults `PORT=7860` (a Hugging Face convention) | `backend/Dockerfile` |
| 8 | `backend/uvicorn.log` is committed | repo root |
| 9 | **`docker-compose.yml` gives Grafana anonymous admin access** — never lift to a public server | `docker-compose.yml` |

---

## 2. Prerequisites — from the System Design Studio plan

**Do not start until all of these exist.** They are built in `System-Design-Studio/AWS-DEPLOYMENT-PLAN.md`, Phases 1, 2, 4, 5, 8.

| Prerequisite | Built in | Verify |
|---|---|---|
| AWS account, root MFA, `kishor-admin` IAM user | SDS Phase 1 | Can sign in as `kishor-admin` |
| Two budgets armed (zero-spend + $30 monthly) | SDS Phase 1.4 | Budgets page shows both |
| Region set to `ap-south-1` | SDS Phase 1.5 | Console top-right |
| EC2 app server `apps-prod` + `apps-sg` | SDS Phase 4 | SSH works |
| Elastic IP attached | SDS Phase 4.3 | IP is stable across restarts |
| Docker + Compose on the app server | SDS Phase 4.4 | `docker run hello-world` |
| **4 GB swap file** | SDS Phase 4.4 | `free -h` — **critical here; PyTorch will OOM without it** |
| Postgres container, **`pgvector/pgvector:pg16`**, named volume | SDS Phase 7.1 | `docker ps` |
| Database `enterprise_knowledge_copilot` created | SDS Phase 7.1 | `\l` in psql |
| Nginx on the host + Let's Encrypt cert | SDS Phase 5 | `https://<duckdns-name>` has a padlock |
| DuckDNS hostname | SDS Phase 5.1 | resolves to the Elastic IP |
| ECR familiarity + lifecycle policy pattern | SDS Phase 6.4 | `system-design-studio` repo exists |
| Backup cron + rollback drill | SDS Phase 8 | a restore has been tested |

> **The Postgres image must be `pgvector/pgvector:pg16`.** Migration `45e87ea2c309` runs `CREATE EXTENSION IF NOT EXISTS vector` and will fail on a stock `postgres:16` image.

---

## 3. Locked decisions

Decided with the user. **Do not re-litigate.**

| Decision | Choice | Reason |
|---|---|---|
| **Deploy order** | **This project second** | 20-min builds vs SDS's 3-min; 3 services vs 1; 13 secrets vs 3 |
| **CI/CD here** | **GitHub Actions**, hosted runners | The 2 GB PyTorch build would OOM the 2 GB Jenkins box; GH runners have 16 GB |
| **CI/CD for SDS** | Jenkins on EC2 | Its light 200 MB build fits there |
| **Compute** | Same shared app server | An ALB alone is $16/mo — kills the budget |
| **Database** | Shared Postgres container, second database | RDS adds ~$15/mo for no benefit at this scale |
| **Not using** | ECS, Fargate, ALB, RDS, Lambda, Amplify | Cost — and **Lambda cannot hold a 2 GB torch image** |
| **Origin layout** | **Single hostname**, `/api/*` → backend | Makes the cross-site cookie problem vanish |
| **Observability stack** | **Not deployed** | Grafana + Prometheus + Phoenix ≈ 600 MB for no user-facing value |
| **Region** | `ap-south-1` (Mumbai) | User is in India |
| **Budget** | Free-tier credits only | User explicitly asked for near-zero cost |

**Why GitHub Actions gets this project:** Jenkins runs on a 2 GB instance the user pays for. Building a 2 GB PyTorch image there means Docker juggling multi-hundred-MB layers alongside a resident JVM — it will OOM, and when it doesn't it takes 20 minutes. GitHub's runners are 4 vCPU / 16 GB RAM / 14 GB disk, free. **Put the heavy build where the capacity is.**

---

## 4. Cost model (verified 2026-09-29)

**AWS changed the Free Tier on 15 July 2025.** Older guides are wrong.

A new account gets **$100 credit at signup + up to $100 more** for onboarding activities (**$200 max**), lasting **6 months** or until spent. The old "750 free hours of t2.micro for 12 months" **does not apply to new accounts**.

So "free" = **keep usage under ~$33/month**.

**Running SDS alone is ~$28/month** (see the sister plan). This project's *incremental* cost:

| Item | Monthly | Notes |
|---|---|---|
| ECR storage for 2 GB images | ~$0.40 | keep the 10-image lifecycle policy |
| **Instance resize `t3.small` → `t3.medium`** | **+$15.20** | only if running both apps at once — see Phase 5 |
| GitHub Actions minutes | **$0** | free on public repos; 2,000 min/mo on private |
| Gemini / Groq API | $0 | free tiers |
| **Incremental total** | **$0.40 to $15.60/mo** | depends on the Phase 5 capacity choice |

**Biggest lever:** stop the app server between demos → the whole setup drops to ~$4/month.

---

## 5. Capacity decision — make this first

This app needs **~1.5 GB**. SDS + Postgres already use **~0.8 GB**. **2.3 GB > the 2 GB on `t3.small`.**

| Option | Cost | Trade-off |
|---|---|---|
| **Resize to `t3.medium`** (4 GB) | +$15.20/mo (~$43 total) | Both apps live together. Simple. Eats credits ~1.5× faster. |
| **Run one app at a time** | $0 | Free, but you must start the right one before a demo |
| **Drop local ML for a hosted embedding API** | $0 | Image 2 GB → 300 MB, RAM 1.5 GB → 400 MB — but needs a code change **and a full re-index**, because 384 dimensions are baked into the schema and the HNSW index |

**Recommended:** resize to `t3.medium` if credits allow; otherwise run one at a time.
Resizing = **stop → change instance type → start**. The EBS disk and Elastic IP survive. Takes about two minutes.

Record the choice in the Progress Tracker before continuing.

---

## 6. Target architecture (this project's slice)

```
  Laptop ──git push──▶ GitHub ──triggers──▶ GITHUB ACTIONS (hosted runner)
                                             │  16 GB RAM, 4 vCPU, 14 GB disk
                                             │  AWS auth: OIDC federation
                                             │  checkout → pytest
                                             │  → docker build (cache: type=gha)
                                             ├──push──▶ Amazon ECR
                                             │        (ekc-backend, ekc-frontend)
                                             └──ssh deploy──┐
                                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │ APP SERVER (t3.small → t3.medium)            │
                    │ ┌──────────────────────────────────────────┐ │
                    │ │ Nginx :80/:443  — ONE hostname           │ │
                    │ │  /api/  → backend  (buffering OFF, 300s) │ │
                    │ │  /      → frontend                       │ │
                    │ └────┬──────────────────────┬──────────────┘ │
                    │  ┌───▼────────────┐  ┌──────▼─────────────┐  │
                    │  │ EKC backend    │  │ EKC frontend :3001 │  │
                    │  │ :8000 (FastAPI)│  │ (Next.js)          │  │
                    │  │ + torch models │  └────────────────────┘  │
                    │  └───┬────────────┘                          │
                    │  ┌───▼─────────────────┐   ┌──────────────┐  │
                    │  │ Postgres 16         │   │ SDS :3000    │  │
                    │  │ + pgvector          │◀──│ (sister app) │  │
                    │  │ shared container    │   └──────────────┘  │
                    │  └─────────────────────┘                     │
                    └──────────────────────────────────────────────┘
                              │
          Gemini · Groq · Google Drive · Slack (external, free tiers)
```

**Why one hostname:** auth is a JWT in an httpOnly cookie. Split hostnames make the browser treat requests as cross-site and **silently drop the cookie**. One nginx hostname with `/api/*` routing removes that entire bug class — see Phase 8.

---

# PHASES

---

## Phase 1 — Repo prep: Docker and config fixes

**Goal:** both services build into images. **Time:** ~2–3 hrs · **Cost:** $0 · **Where:** the laptop

### 1.1 Create `frontend/Dockerfile`

**It does not exist.** Multi-stage, same shape as the SDS Dockerfile but **without Prisma**:

```dockerfile
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* is baked in at BUILD time, not runtime
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
```

> **`NEXT_PUBLIC_API_URL` is baked in at build time.** Changing it later requires **rebuilding the image**, not just restarting the container. Pass it as a `--build-arg` from the workflow.

### 1.2 Edit `frontend/next.config.ts`

Currently an empty config. Add:

```ts
const nextConfig = { output: "standalone" };
```

Without it the runtime image needs all of `node_modules` (~500 MB).

### 1.3 Bake the ML models into the backend image — highest-value change here

Today both models download from HuggingFace **on the first question**, so the first query appears to hang for 60+ seconds. Add to `backend/Dockerfile`, after `pip install`:

```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('BAAI/bge-small-en-v1.5'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

This caches ~220 MB into an image layer. **The single biggest user-visible improvement available.** It also means the container needs no HuggingFace egress at runtime.

### 1.4 Other backend Dockerfile changes

- **Default `PORT` `7860` → `8000`.** 7860 is a Hugging Face Spaces convention and is confusing here.
- **Remove `alembic upgrade head` from `CMD`.** It becomes a discrete pipeline step (Phase 7). Leaving it in `CMD` means every container restart races on migrations.

### 1.5 Config cleanups

- `observability/prometheus.yml` — target `host.docker.internal:8000` → `backend:8000`. The current value is Docker-Desktop-on-Windows only and does not exist on Linux.
- `frontend/src/app/app/agent-ops/page.tsx:14-15` — replace the hardcoded `localhost:3001` (Grafana) and `localhost:6006` (Phoenix) with env vars, and **hide the panel when they're unset**. The observability stack is not deployed.
- Add `backend/uvicorn.log` to `.gitignore` and remove it from tracking.
- **Do not deploy `docker-compose.yml` as-is** — it grants Grafana anonymous admin access.

### 1.6 Create `docker-compose.prod.yml`

Three services referencing **ECR images via `${IMAGE_TAG}`**, not local builds:
- `backend` — port 8000 internal only, env from `.env.prod`
- `frontend` — port 3001 internal only
- (Postgres already runs as a shared container from the SDS plan — **do not start a second one**)

All with `restart: unless-stopped`.

### 1.7 Verify locally

```bash
docker compose -f docker-compose.prod.yml up --build
```

Sign up → log in → send a chat message → **confirm it streams word by word**.

**If it doesn't work on the laptop, it will not work on AWS.**

**Exit criteria:** both images build · stack starts · signup works · chat streams · models load without a download pause

---

## Phase 2 — ECR repositories

**Time:** ~15 min · **Cost:** ~$0.40/month

Create two **private** repositories: `ekc-backend`, `ekc-frontend`.

Add a **lifecycle policy: keep the last 10 images** to each. At ~2 GB per backend image this matters more here than for SDS.

---

## Phase 3 — AWS OIDC for GitHub Actions

**Goal:** Actions authenticates to AWS with **no stored credentials**.
**Time:** ~45 min · **Cost:** $0

This is the highest-value interview item in this plan. Do it properly.

### 3.1 Create the OIDC identity provider
IAM → **Identity providers** → **Add provider** → OpenID Connect
- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

### 3.2 Create the role
Create an IAM role with a trust policy that federates to that provider and **restricts the `sub` claim to this repository only** — e.g. `repo:KishorKumar07/Enterprise-knowledge-copilot:ref:refs/heads/main`.

**Scope the trust to the repo and branch.** A wildcard `repo:*` would let *any* GitHub repository assume your role.

Attach `AmazonEC2ContainerRegistryPowerUser`.

### 3.3 Use it in the workflow

```yaml
permissions:
  id-token: write     # required for OIDC
  contents: read
```

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::<account-id>:role/github-actions-ekc
    aws-region: ap-south-1
```

**Why this matters:** the lazy alternative is storing `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` as repo secrets — long-lived credentials sitting in GitHub that never expire and don't rotate. OIDC issues a short-lived token per run.

> *"I used OIDC federation so no static AWS credentials exist anywhere."* Most candidates don't know this bar exists.

**Exit criteria:** a trivial workflow can run `aws sts get-caller-identity` with no stored keys

---

## Phase 4 — The GitHub Actions pipeline

**Goal:** `git push` → test, build, push to ECR, deploy.
**Time:** 3–4 hrs · **Cost:** $0

Create `.github/workflows/deploy.yml`. **This repo has no CI at all today**, so this is also its first test automation.

### 4.1 Stages

| # | Step | Notes |
|---|---|---|
| 1 | `actions/checkout@v4` | |
| 2 | `setup-python@v5` + `pip install -r backend/requirements.txt` | cache pip |
| 3 | **`pytest`** (working dir `backend/`) | `backend/tests/` — **first-ever CI run for this repo** |
| 4 | `aws-actions/configure-aws-credentials@v4` with OIDC | Phase 3 |
| 5 | `aws-actions/amazon-ecr-login@v2` | |
| 6 | `docker/build-push-action@v6` — backend, **`cache-from/to: type=gha`** | see 4.2 |
| 7 | Same for frontend, with `NEXT_PUBLIC_API_URL` as a build arg | parallel job or matrix |
| 8 | `appleboy/ssh-action` → pull, `alembic upgrade head`, `docker compose up -d` | see 4.3 |
| 9 | Health check against `/api/health` | retry ~10× with a 6s gap |

Tag every image with **both** the git SHA and `latest`. Without a SHA tag you cannot roll back and cannot tell which commit is live.

### 4.2 Layer caching is not optional here

```yaml
- uses: docker/build-push-action@v6
  with:
    context: ./backend
    push: true
    tags: ${{ steps.login-ecr.outputs.registry }}/ekc-backend:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

A 2 GB torch image without `type=gha` cache **re-downloads PyTorch on every run** — minutes and patience gone. With it, unchanged layers are reused and builds drop from ~20 min to ~3.

**Verification that it's working:** the second build must be dramatically faster than the first. If it isn't, the cache isn't wired up.

### 4.3 Migrations as a discrete step

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d backend frontend
```

**Never in the container `CMD`** — that races on every restart.

### 4.4 Optional but worth it

`environment: production` with a **required reviewer** gives a manual approval gate before deploy — a one-line way to demonstrate you think about change control.

### 4.5 Actions minutes

Private repos get **2,000 free minutes/month** (a 20-min build = 100 builds; with caching, far more). **Public repos are unlimited** — and this is a portfolio project, so making it public costs nothing and removes the limit.

### 4.6 The contrast worth articulating

Jenkins (sister project) authenticates to AWS via an **IAM instance role** because it's a long-lived server with an identity. Actions authenticates via **OIDC** because runners are ephemeral and federate per run. **Same "no stored credentials" principle, two mechanisms, because the execution models differ.**

**Exit criteria:** push triggers the workflow · pytest runs · both images reach ECR SHA-tagged · second build is much faster · a broken test blocks the deploy · health check passes

---

## Phase 5 — Resize the instance (if chosen)

Per Section 5. Stop `apps-prod` → **Actions → Instance settings → Change instance type** → `t3.medium` → start.

The EBS disk and Elastic IP survive. Confirm with `free -h` that you now have ~4 GB.

---

## Phase 6 — Nginx routing

**Goal:** one hostname serving both tiers. **Time:** ~45 min

Add to the existing nginx config from the SDS plan:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;

    # Chat streams Server-Sent Events (backend/app/services/chat_stream.py).
    # With buffering ON, answers arrive in one lump at the end and the app feels broken.
    proxy_buffering off;
    proxy_cache off;

    # LLM answers and Drive/Slack ingestion exceed nginx's 60s default.
    proxy_read_timeout 300s;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
    proxy_pass http://127.0.0.1:3001;
    # ...same proxy_set_header block
}
```

**These two settings cause the most confusing bugs in this whole deployment.** Buffering on → streaming silently breaks. Timeout at 60s → long answers get cut off with no clear error.

---

## Phase 7 — Environment and database

### 7.1 Database

Use the **existing shared Postgres container** (`pgvector/pgvector:pg16`) from the SDS plan. Do not start a second one.

The `enterprise_knowledge_copilot` database should already exist. Migration `45e87ea2c309` runs `CREATE EXTENSION IF NOT EXISTS vector` — **it will fail on a stock `postgres:16` image.**

**`DATABASE_URL` must use the `postgresql+asyncpg://` driver prefix.** `backend/alembic/env.py` reads the URL directly from settings (deliberately bypassing `alembic.ini`, whose `sqlalchemy.url` is a dummy) and needs the async driver.

### 7.2 Production environment values

| Variable | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `production` | |
| `DATABASE_URL` | `postgresql+asyncpg://ekc:<pw>@postgres:5432/enterprise_knowledge_copilot` | **`+asyncpg` is required** |
| `JWT_SECRET` | `openssl rand -hex 32` | never reuse the dev value |
| `CREDENTIAL_ENCRYPTION_KEY` | a Fernet key | **lose this and every stored OAuth token is permanently undecryptable — back it up** |
| `FRONTEND_ORIGIN` | `https://<duckdns-name>` | must match **character for character** — CORS is a single-origin allowlist in `backend/app/main.py` |
| `COOKIE_SECURE` | `true` | |
| `COOKIE_SAMESITE` | `lax` | correct **because** we're single-origin; `none` would only be needed for split domains |
| `NEXT_PUBLIC_API_URL` | `https://<duckdns-name>` | **build-time** — rebuild the image to change it |
| `GOOGLE_REDIRECT_URI` | production callback | Phase 9 |
| `SLACK_REDIRECT_URI` | production callback | Phase 9 |
| `GEMINI_API_KEY` / `GROQ_API_KEY` | user's keys | free tiers |
| `OTEL_ENABLED` | `false` | Phoenix is not deployed |

Store as `/opt/apps/ekc/.env.prod`, **`chmod 600`**. Never commit.

---

## Phase 8 — The cookie problem (read before debugging login)

Auth is a JWT in an **httpOnly cookie** `ekc_session` (`backend/app/api/auth.py`).

If the frontend and backend sit on **different hostnames**, the browser treats requests as cross-site and **silently refuses to send the cookie** unless both are HTTPS *and* the cookie is `SameSite=None; Secure`. There is no error message. Login appears to succeed, then every subsequent page bounces back to `/login`.

**This plan avoids the whole problem** by serving both from one nginx hostname (Phase 6). Then:
- `COOKIE_SAMESITE=lax` is correct
- `COOKIE_SECURE=true` (you have HTTPS)
- `FRONTEND_ORIGIN` must match exactly
- CORS is trivial

`backend/app/core/config.py:19-22` documents this exact trade-off in a comment.

**Also note:** OAuth CSRF `state` is a short-lived JWT signed with `JWT_SECRET` (`backend/app/services/oauth_state.py`) — stateless, so it survives restarts and would survive multi-instance. Nothing to do here; just don't rotate `JWT_SECRET` mid-flow.

---

## Phase 9 — OAuth consoles

**Google Cloud Console** → OAuth client → Authorised redirect URIs → add the production callback.
**Slack API dashboard** → OAuth & Permissions → Redirect URLs → add the equivalent.

Then set `GOOGLE_REDIRECT_URI` and `SLACK_REDIRECT_URI` to match.

**Confirm the exact callback paths** in `backend/app/api/google_drive.py` and `backend/app/api/slack.py` before pasting. A one-character mismatch gives `redirect_uri_mismatch` and nothing else.

Google scopes in use: `drive.readonly`, `userinfo.email`.

---

## Phase 10 — Verify

In order — don't skip ahead:

1. `curl -f https://<host>/api/health` → backend alive
2. `https://<host>` loads, padlock green
3. Sign up → log in → **confirm `ekc_session` appears** in DevTools → Application → Cookies
4. Refresh → **still logged in**
5. Send a chat message → **the answer streams word by word** (all at once = nginx buffering still on)
6. **First query should be fast** — no 60s model-download pause (proves Phase 1.3 worked)
7. Connect Google Drive → OAuth completes → run a sync → watch `docker compose logs -f backend`
8. Connect Slack → same
9. Ask a question about ingested content → the answer **cites real sources**
10. Reboot the instance → everything returns with no manual steps

---

## 11. Interview material

**"You used both Jenkins and GitHub Actions — why?"**
> "Build weight. Jenkins is self-hosted on a 2 GB instance — fine for the other project's 200 MB Node image, but it would OOM on this one's 2 GB PyTorch build, so that runs on GitHub's 16 GB hosted runners. Both push to the same ECR registry and the app server only ever pulls, so the CI tool is an implementation detail behind a common contract. The auth differs too: Jenkins uses an IAM instance role because it's a long-lived server with an identity; Actions uses OIDC federation because runners are ephemeral. Same 'no stored credentials' principle, two mechanisms."

**"What breaks first when you scale this?"**
> "Two things. Ingestion runs in-process via FastAPI `BackgroundTasks` (`backend/app/api/slack.py:201`, `google_drive.py:215`) — with two instances behind a load balancer, a sync job dies whenever its instance is recycled. That belongs on SQS with a dedicated worker; the empty `backend/app/workers/` package is where it'd go. Second, rate limiting is in-memory via slowapi, so each instance would enforce its own separate limit — that needs Redis."
> *(Not a guess — it's documented in a comment in `backend/app/core/rate_limit.py`.)*

**"Why pgvector instead of Pinecone?"**
> "One datastore instead of two — no dual-write consistency problem, no extra cost, and transactional consistency between documents and their chunk embeddings. Postgres with an HNSW index handles this dataset comfortably. At tens of millions of vectors I'd revisit it."

**"Why run embeddings locally?"**
> "Cost and latency — bge-small is 384-dimensional and runs in milliseconds on CPU, with no per-token charge on every chunk of every document. The trade-off is memory: PyTorch forces a 2 GB image and rules out Lambda entirely. If I needed serverless I'd swap to a hosted embedding API and re-index."

**"Why one EC2 instead of ECS Fargate?"**
> "Cost. An ALB is ~$16/month before serving a request and RDS another $15 — my whole credit budget in five weeks for a project with one user. The containers and pipelines are already built, so moving to ECS is a task-definition away if traffic justified it."

**"How do you handle secrets?"**
> "OIDC federation for AWS so no static credentials exist, GitHub encrypted secrets for the API keys, and a `chmod 600` env file on the host. In a team setting I'd move to AWS Secrets Manager. The OAuth provider tokens are already Fernet-encrypted at rest at the application layer."

### Optional upgrades, best value first

| Upgrade | Learning value | Cost |
|---|---|---|
| **Terraform the whole thing** | Very high — IaC is a real hiring signal | $0 |
| **SQS + a real worker for ingestion** | Very high — fixes the actual architectural weakness | ~$0 at this volume |
| **AWS Secrets Manager** | High | ~$0.40/mo |
| **CloudWatch Logs agent** | Medium | ~$0.50/mo |
| **ECS Fargate + ALB** | High, but expensive | +$35/mo |

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| **Build killed at the torch step** | Out of memory | Build on GH Actions, not the server; ensure 4 GB swap if building locally |
| Login succeeds but every page bounces to `/login` | Cookie not stored | `COOKIE_SECURE=true` needs HTTPS; `FRONTEND_ORIGIN` must match exactly — Phase 8 |
| **Chat answer arrives all at once** | Nginx buffering SSE | `proxy_buffering off` on `/api/` — Phase 6 |
| 504 after ~60s | Nginx default read timeout | `proxy_read_timeout 300s` |
| `relation "users" does not exist` | Migrations didn't run | `alembic upgrade head` in the backend container |
| **First question takes 60+ seconds** | Models downloading at runtime | Bake them into the image — Phase 1.3 |
| `CREATE EXTENSION vector` fails | Wrong Postgres image | Must be `pgvector/pgvector:pg16` |
| Alembic can't connect | Missing async driver prefix | `postgresql+asyncpg://` |
| `redirect_uri_mismatch` | OAuth console not updated, or path mismatch | Phase 9 |
| Frontend calls `localhost:8000` in prod | `NEXT_PUBLIC_API_URL` baked in at build | **Rebuild the image** with the right build arg |
| Sync job dies partway | Instance recycled mid-`BackgroundTask` | Known limitation — restart the sync |
| Can't decrypt stored OAuth tokens | `CREDENTIAL_ENCRYPTION_KEY` changed or lost | **Unrecoverable** — users must reconnect |
| OOM after adding this app | Still on `t3.small` | Section 5 capacity decision |
| Actions build is slow every time | `type=gha` cache not wired up | Phase 4.2 |
| Actions can't reach AWS | OIDC trust policy `sub` doesn't match the branch | Phase 3.2 |

---

## 13. Progress tracker

### Prerequisites
- [ ] SDS plan Phases 1, 2, 4, 5, 8 complete (Section 2 table all verified)
- [ ] Postgres container confirmed to be `pgvector/pgvector:pg16`
- [ ] `enterprise_knowledge_copilot` database exists
- [ ] 4 GB swap active on the app server

### Capacity decision (Section 5)
- [ ] Chosen: ☐ resize to `t3.medium`  ☐ run one app at a time  ☐ drop local ML

### Phases

| Phase | Status | Notes |
|---|---|---|
| 1 — Repo prep (Dockerfiles, config fixes) | ☐ Not started | |
| 2 — ECR repositories | ☐ Not started | |
| 3 — AWS OIDC for Actions | ☐ Not started | |
| 4 — GitHub Actions pipeline | ☐ Not started | |
| 5 — Instance resize (if chosen) | ☐ Not started | |
| 6 — Nginx routing | ☐ Not started | |
| 7 — Environment + database | ☐ Not started | |
| 8 — Cookie configuration | ☐ Not started | |
| 9 — OAuth consoles | ☐ Not started | |
| 10 — Verify | ☐ Not started | |

### Values to fill in

| Item | Value |
|---|---|
| AWS account ID | |
| OIDC role ARN | |
| ECR registry URL | |
| Public hostname | |
| Instance type in use | |
| `CREDENTIAL_ENCRYPTION_KEY` backed up? | ☐ |

### Final checklist

**App**
- [ ] `https://<host>/api/health` returns OK
- [ ] Signup → login → refresh → still logged in
- [ ] `ekc_session` cookie visible in DevTools
- [ ] Chat answers **stream word by word**
- [ ] First query is fast (models pre-baked)
- [ ] Google Drive OAuth completes; sync ingests documents
- [ ] Slack OAuth completes; sync ingests messages
- [ ] Answers cite real ingested sources

**GitHub Actions pipeline**
- [ ] `git push` triggers the workflow
- [ ] `pytest` runs (this repo's first CI run)
- [ ] AWS auth uses **OIDC** — no `AWS_ACCESS_KEY_*` secrets in the repo
- [ ] OIDC trust policy is scoped to this repo and branch, not a wildcard
- [ ] Both images reach ECR, SHA-tagged
- [ ] **Second build is much faster than the first** (proves layer caching)
- [ ] A broken test blocks the deploy
- [ ] Deploy ends with a passing health check

**Infrastructure**
- [ ] Full reboot → everything returns with no manual steps
- [ ] Both databases included in the `pg_dump` backup cron
- [ ] Rollback to a previous SHA tested
- [ ] Ports 5432 / 8000 / 3001 **not** reachable publicly
- [ ] Budgets still armed; spend tracking against credits

---

## 14. Time estimate

| Phase | Time |
|---|---|
| 1 — Repo prep | 2–3 hrs |
| 2 — ECR | 15 min |
| 3 — OIDC | 45 min |
| 4 — **Actions pipeline** | **3–4 hrs** |
| 5 — Resize | 15 min |
| 6 — Nginx | 45 min |
| 7 — Env + DB | 45 min |
| 8 — Cookies | 30 min |
| 9 — OAuth consoles | 45 min |
| 10 — Verify | 1 hr |
| **Total** | **~1.5 focused days** |

Phases 1 and 4 are where the time goes.
