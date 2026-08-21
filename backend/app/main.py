import logging

from app.core.ssl_bundle import install as install_ca_bundle

install_ca_bundle()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402

from app.api.agent_ops import router as agent_ops_router  # noqa: E402
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.google_drive import router as google_drive_router
from app.api.slack import router as slack_router
from app.api.sync_jobs import router as sync_jobs_router
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.tracing import setup_tracing

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ekc")

# agent_ops: OTel spans -> Phoenix (self-hosted), before any LLM SDK client
# gets instantiated so the OpenInference auto-instrumentation patches apply.
setup_tracing(settings)

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.1.0")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# agent_ops: HTTP-level metrics (request rate, latency, in-progress) exposed
# at /metrics for Prometheus to scrape -> visualized in Grafana.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a moment and try again."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(google_drive_router)
app.include_router(slack_router)
app.include_router(sync_jobs_router)
app.include_router(agent_ops_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
