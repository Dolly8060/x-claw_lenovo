from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


REQUEST_COUNT = Counter("xclaw_requests_total", "Total requests", ["platform", "status", "task_type"])
REQUEST_LATENCY = Histogram("xclaw_request_latency_seconds", "Request latency seconds", ["task_type"])
TOOL_CALL_COUNT = Counter("xclaw_tool_calls_total", "Tool calls", ["server_name", "tool_name", "status"])


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

