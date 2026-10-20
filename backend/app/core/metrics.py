"""Custom Prometheus metrics for the agent pipeline, on top of the automatic
HTTP-level metrics that prometheus-fastapi-instrumentator adds in main.py.
Both share the default registry, so everything shows up on one /metrics.
"""

from prometheus_client import Counter, Histogram

agent_node_duration_seconds = Histogram(
    "agent_node_duration_seconds",
    "LangGraph node execution time",
    labelnames=["node"],
)

agent_node_total = Counter(
    "agent_node_total",
    "LangGraph node executions",
    labelnames=["node", "status"],
)

agent_run_duration_seconds = Histogram(
    "agent_run_duration_seconds",
    "End-to-end agent graph run time (one user turn)",
)

agent_run_total = Counter(
    "agent_run_total",
    "Agent graph runs",
    labelnames=["status"],
)

# LLM provider health: which model answered, which failed, and how often the
# fallback had to take over. Labelled by provider so a slow or failing primary
# is visible on the dashboard instead of only in the logs.
llm_call_total = Counter(
    "llm_call_total",
    "LLM provider calls",
    labelnames=["provider", "kind", "outcome"],  # kind: complete|stream, outcome: success|error
)

llm_fallback_total = Counter(
    "llm_fallback_total",
    "Times a provider failed and the next one was tried",
    labelnames=["from_provider", "to_provider"],
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "complete(): whole call. stream: time to the first token.",
    labelnames=["provider", "kind"],
    buckets=(0.25, 0.5, 1, 2, 3, 5, 8, 12, 20, 30, 60),
)
