"""Prometheus request metrics (Stage 5.3).

Pure-ASGI middleware — no FastAPI/Starlette import — recording a request
counter and a latency histogram. ``prometheus_client`` is an optional extra
(see infra/requirements-monitoring.txt) and is lazy-imported inside the
factories, so importing this module never requires it.
"""
from __future__ import annotations

import time

REQUEST_COUNT_METRIC = "http_requests_total"
REQUEST_LATENCY_METRIC = "http_request_duration_seconds"

_METRICS = None  # (counter, histogram), created once on first factory call


def _load_prometheus():
    try:
        import prometheus_client
    except ImportError as exc:
        raise RuntimeError(
            "prometheus_client is required for request metrics but is not "
            "installed; install the optional monitoring extras: "
            "pip install -r infra/requirements-monitoring.txt"
        ) from exc
    return prometheus_client


def _metrics():
    global _METRICS
    if _METRICS is None:
        prom = _load_prometheus()
        _METRICS = (
            prom.Counter(REQUEST_COUNT_METRIC, "Total HTTP requests.",
                         ["method", "path", "status"]),
            prom.Histogram(REQUEST_LATENCY_METRIC,
                           "HTTP request latency in seconds.",
                           ["method", "path"]),
        )
    return _METRICS


def metrics_middleware():
    """Return a pure-ASGI middleware class recording count + latency.

    Wire it with ``app.add_middleware(metrics_middleware())`` (any ASGI app).
    Raises RuntimeError if prometheus_client is not installed.
    """
    requests_total, request_latency = _metrics()

    class _MetricsMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            status = {"code": "500"}  # if the app crashes before responding

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status["code"] = str(message["status"])
                await send(message)

            start = time.perf_counter()
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                method = scope.get("method", "")
                path = scope.get("path", "")
                requests_total.labels(method=method, path=path,
                                      status=status["code"]).inc()
                request_latency.labels(method=method, path=path).observe(
                    time.perf_counter() - start)

    return _MetricsMiddleware


def metrics_endpoint() -> str:
    """Prometheus exposition text for a /metrics route.

    Raises RuntimeError if prometheus_client is not installed.
    """
    prom = _load_prometheus()
    return prom.generate_latest().decode("utf-8")
