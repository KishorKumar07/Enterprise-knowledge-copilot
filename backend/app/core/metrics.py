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
