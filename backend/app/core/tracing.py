"""OpenTelemetry setup for agent_ops.

Traces export to a self-hosted Arize Phoenix instance (see docker-compose.yml)
over OTLP/HTTP — swap PHOENIX_ENDPOINT for any other OTLP collector (Jaeger,
Tempo, a vendor) without touching application code.

The Gemini and Groq SDK clients are auto-instrumented via OpenInference, so
every LLM call becomes a child span with prompt/completion/token-usage
attributes attached automatically — app/services/llm.py needed no changes.
Export failures are non-fatal: the BatchSpanProcessor just logs and drops.
"""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings

logger = logging.getLogger("ekc.tracing")

_tracer = trace.get_tracer("ekc.agents")


def get_tracer() -> trace.Tracer:
    return _tracer


def setup_tracing(settings: Settings) -> None:
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false)")
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "ekc-backend"}))
    exporter = OTLPSpanExporter(endpoint=f"{settings.phoenix_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        GoogleGenAIInstrumentor().instrument()
    except Exception:
        logger.warning("Failed to instrument google-genai SDK for tracing", exc_info=True)

    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
    except Exception:
        logger.warning("Failed to instrument OpenAI-compatible SDK for tracing", exc_info=True)

    logger.info("OpenTelemetry tracing enabled -> %s/v1/traces", settings.phoenix_endpoint)
