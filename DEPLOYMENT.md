# Deployment

Live demo: **https://kishor-ekc.duckdns.org**

This project runs on a single AWS EC2 server and is deployed automatically by GitHub Actions.
Pushing to `main` runs the tests, builds the container images, pushes them to Amazon ECR, rolls
the new release out to the server and checks that the public site is healthy. There are no
long-lived AWS credentials anywhere in the pipeline.

## Architecture

```
  git push ──▶ GitHub Actions ─────────────────────────────────────────────┐
               1. CI: ruff, import check, 23 unit tests, migrations         │
                  up/down/up on a pgvector Postgres, frontend lint/types/build
               2. Build backend + frontend images in parallel (layer cache) │
               3. Push to Amazon ECR, tagged with the git SHA               │
               4. Ask the server to roll out that SHA via AWS SSM           │
               5. Poll https://…/api/health until it answers                │
                                                                            ▼
   Browser ──HTTPS──▶ Nginx (Let's Encrypt) on an EC2 instance ◀── ECR (pull only)
                       ├─ /          ▶ Next.js frontend      (127.0.0.1:3100)
                       ├─ /api/      ▶ FastAPI backend       (127.0.0.1:7860)
                       ├─ /grafana/  ▶ Grafana               (own login)
                       └─ /phoenix/  ▶ Arize Phoenix         (HTTP basic auth)
                      Docker network (not reachable from outside):
                       Postgres + pgvector · Prometheus · the services above
                      Nightly pg_dump ▶ S3 (30-day retention)
```

Six containers make up the app: frontend, backend, Postgres+pgvector, Prometheus, Grafana and
Phoenix. Only the frontend and backend are built here (and stored in ECR); the other four are
public images. Every port is bound to `127.0.0.1`, so Nginx is the only way in.

## Key decisions

| Decision | Why |
|---|---|
| **GitHub Actions + OIDC**, not stored AWS keys | The runner swaps a short-lived signed token for temporary AWS credentials. The IAM trust policy is pinned to this repository and the `main` branch, so no other repo or branch can assume the role |
| **Build on the runner, never on the server** | The backend image is ~2 GB (CPU PyTorch plus two embedding/reranking models baked in). The server only pulls, so a broken build cannot reach production and a deploy takes about a minute |
| **Deploy through AWS SSM, not SSH** | GitHub's runners have unpredictable IPs, so SSH would need port 22 open to the internet and a private key stored in GitHub. SSM sends the commands over the AWS API: no inbound port, no key |
| **Migrations are a separate step**, run before the new containers start | Not in the container `CMD`: a restart must not re-run them, and a failed migration should fail the deploy instead of crash-looping |
| **Images tagged by git SHA** | Rollback is one command and you can always tell which commit is live |
| **Models baked into the image** | Otherwise the first user request downloads ~220 MB from Hugging Face and times out |
| **Own Postgres container for this app** | Isolated from the other app on the same host |
| **Groq first, Gemini as fallback** (`LLM_PRIMARY`) | From this server Gemini calls took 10-20 s and sometimes timed out; Groq answers in ~1 s. A provider that fails before producing output hands over to the next one; a stream is never switched mid-answer |

## Observability

Every LangGraph node run produces three things at once: an OpenTelemetry span (Phoenix), a
Prometheus metric (Grafana) and a durable `agent_steps` row in Postgres (the in-app Agent Ops
page). The LLM layer adds `llm_call_total`, `llm_fallback_total` and `llm_latency_seconds`, so a
failing or slow provider shows up on the dashboard.

## Alerting

Application behaviour is watched by Prometheus, Grafana and Phoenix, which run on the same box as
the app and so cannot report their own death. Host-level problems are watched from outside by
**CloudWatch alarms**, all sending email through one SNS topic:

| Alarm | Fires when |
|---|---|
| CPU | average CPU above 80% for 10 minutes |
| Status check | the EC2 system or instance health check fails twice in a row |
| Memory | `mem_used_percent` above 85% (CloudWatch agent) |
| Disk | `disk_used_percent` on `/` above 80% (CloudWatch agent) |

The alarm path was proven end to end: a first memory alarm with a mistyped threshold fired and the
email arrived. Memory and disk need the CloudWatch agent (`deploy/cloudwatch-agent.sh`) because EC2
only reports CPU, network and health checks from the outside. SSH access from a personal IP was
removed; the browser-based Session Manager terminal and the SSM deploy path need no inbound port.

## Verified, not assumed

- **Restore test:** a backup pulled from S3 was restored into a scratch database; all 12 tables
  and every row count matched, and the pgvector extension came back.
- **Rollback drill:** back to the previous release in ~22 s, forward again in ~18 s, data intact.
- **Reboot test:** after a full instance reboot all containers and both sites returned on their
  own within ~30 s, and logged-in sessions survived.
- **Nothing exposed:** Postgres, the backend, Prometheus and the internal ports are unreachable
  from the internet; Grafana and Phoenix require a password.
- **A failing test blocks the deploy:** see the demonstration at the end.

## Problems hit and what they taught

| Symptom | Cause | Fix |
|---|---|---|
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | New GitHub repos use an *immutable OIDC subject* with numeric owner and repo IDs (`repo:OWNER@ID/REPO@ID:ref:…`), so a trust policy written with plain names never matched | Read the real value from `GET /repos/…/actions/oidc/customization/sub` and use it in the trust policy |
| CI typecheck failed only on GitHub | `LayoutProps` is generated into `.next/`; a clean checkout has none | Run `next typegen` before `tsc` |
| Phoenix page loaded but showed no data | With `PHOENIX_HOST_ROOT_PATH` it expects the proxy to **strip** the prefix | `proxy_pass http://127.0.0.1:6006/;` |
| Answers took ~36 s | Gemini silently timed out after 20 s, then the fallback answered | Groq first, 20 s fail-fast timeout, fallback metric and chart |
| Prometheus charts empty after deploy | Scrape target pointed at `host.docker.internal:8000` | Scrape `backend:7860` on the compose network |
| `t3.medium` rejected | The AWS Free plan only allows specific instance types | Used `c7i-flex.large` (4 GB) |
| Docker builds failed on one laptop | Antivirus HTTPS scanning re-signs traffic with its own root CA | Trust that root in local builds only (git-ignored); CI and the server stay strict |
| CI ran twice per push | Both `ci.yml` and `deploy.yml` triggered it and shared a concurrency group | CI runs on pull requests and through `workflow_call` only |

## Jenkins vs GitHub Actions (built both)

| | Jenkins (System Design Studio) | GitHub Actions (this project) |
|---|---|---|
| Runs on | An EC2 box I patch and pay for | GitHub's runners, free for a public repo |
| Setup | Hours: Java, plugins, credentials, hardening | Minutes: commit a YAML file |
| Build capacity | 2 GB: could not have built this 2 GB image | 16 GB runner |
| AWS auth | IAM instance role (box is trusted) | OIDC: short-lived, scoped to one repo and branch |
| Triggers | Poll every 5 min to keep port 8080 private | Native events, instant, no inbound port |
| Parallelism | Stages run in sequence | Jobs run in parallel by default |
| State | Workspace persists | Runner is destroyed: caching must be explicit |
| Security burden | Plugin CVEs and patching are mine | GitHub's |

Match the build to the executor: a small Node build fits a small Jenkins box; a 2 GB PyTorch image
needs a bigger runner.

## Operating it

```bash
# roll back (on the server, as root)
cd /opt/apps/ekc && IMAGE_TAG=<older-sha> ECR_REGISTRY=<registry> docker compose up -d backend frontend

# logs
docker logs --tail 100 ekc-backend
```

### Stopping and starting the server (to save credits)

The instance is stopped between demos. It keeps its Elastic IP, disk and DNS names, and everything
restarts by itself (containers have `restart: unless-stopped`; Nginx, Docker and the SSM agent are
enabled at boot).

| Step | When |
|---|---|
| EC2 → select the instance → **Instance state → Stop** (never *Terminate*, which deletes it) | after the last push has deployed |
| GitHub → Settings → Secrets and variables → Actions → Variables → set `DEPLOY_ENABLED` to `false` | while it is stopped, otherwise the deploy job fails because nothing answers over SSM |
| **Start** the instance, wait ~3 minutes, open the site | before a demo |
| Set `DEPLOY_ENABLED` back to `true` | after it is running again |

- Let's Encrypt certificates (90 days) renew only while the server is running. Start it at least
  once every couple of months; if the site ever shows a certificate error after a long stop, run
  `sudo certbot renew` in a Session Manager terminal.
- Stopped, the bill is only the disk, the Elastic IP, ECR and S3 (a few dollars a month).
- Documentation-only pushes (`*.md`) do not trigger a deploy.

## Demonstration: a bad commit cannot deploy

Run the *Deploy* workflow manually (Actions → Deploy → Run workflow) on a branch that contains a
failing test. The `CI` job goes red and the **build, deploy and verify jobs are skipped**, so
nothing reaches ECR or the server. Even if CI were green on a branch, the AWS trust policy only
accepts tokens from `main`.
