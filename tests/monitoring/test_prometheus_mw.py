"""Prometheus middleware tests (offline; prometheus_client NOT required).

The module must import without the lib; the factories must raise a clear
RuntimeError without it; middleware behaviour is exercised against a stub
prometheus_client injected into sys.modules.
"""
from __future__ import annotations

import asyncio
import sys
import types

import pytest

from src.monitoring import prometheus_mw


def test_module_imports_without_prometheus_client():
    # The top-of-file import already proves this; make the intent explicit.
    assert hasattr(prometheus_mw, "metrics_middleware")
    assert hasattr(prometheus_mw, "metrics_endpoint")


def test_factory_raises_runtime_error_without_lib(monkeypatch):
    monkeypatch.setitem(sys.modules, "prometheus_client", None)  # force ImportError
    monkeypatch.setattr(prometheus_mw, "_METRICS", None)
    with pytest.raises(RuntimeError, match="prometheus_client") as excinfo:
        prometheus_mw.metrics_middleware()
    assert "infra/requirements-monitoring.txt" in str(excinfo.value)


def test_endpoint_raises_runtime_error_without_lib(monkeypatch):
    monkeypatch.setitem(sys.modules, "prometheus_client", None)
    with pytest.raises(RuntimeError, match="prometheus_client") as excinfo:
        prometheus_mw.metrics_endpoint()
    assert "infra/requirements-monitoring.txt" in str(excinfo.value)


# --- middleware behaviour against a stub prometheus_client -------------------

class _FakeMetric:
    def __init__(self, name, doc, labelnames):
        self.name = name
        self.labelnames = labelnames
        self.events = []  # ("inc"|"observe", labels[, value])
        self._labels = None

    def labels(self, **labels):
        self._labels = labels
        return self

    def inc(self):
        self.events.append(("inc", self._labels))

    def observe(self, value):
        self.events.append(("observe", self._labels, value))


def _stub_prometheus(monkeypatch):
    stub = types.ModuleType("prometheus_client")
    stub.created = []

    def _make(name, doc, labelnames):
        metric = _FakeMetric(name, doc, labelnames)
        stub.created.append(metric)
        return metric

    stub.Counter = _make
    stub.Histogram = _make
    stub.generate_latest = lambda: b"# HELP stub\n"
    monkeypatch.setitem(sys.modules, "prometheus_client", stub)
    monkeypatch.setattr(prometheus_mw, "_METRICS", None)
    return stub


def test_middleware_records_count_and_latency(monkeypatch):
    stub = _stub_prometheus(monkeypatch)
    middleware_cls = prometheus_mw.metrics_middleware()

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    scope = {"type": "http", "method": "POST", "path": "/api/v1/score"}
    asyncio.run(middleware_cls(app)(scope, receive, send))

    assert [m["type"] for m in sent] == ["http.response.start",
                                         "http.response.body"]
    counter, histogram = stub.created
    assert counter.name == "http_requests_total"
    assert counter.events == [("inc", {"method": "POST",
                                       "path": "/api/v1/score",
                                       "status": "200"})]
    assert histogram.name == "http_request_duration_seconds"
    (event, labels, value), = histogram.events
    assert (event, labels) == ("observe", {"method": "POST",
                                           "path": "/api/v1/score"})
    assert value >= 0


def test_middleware_records_500_when_app_crashes(monkeypatch):
    stub = _stub_prometheus(monkeypatch)
    middleware_cls = prometheus_mw.metrics_middleware()

    async def broken_app(scope, receive, send):
        raise ValueError("boom")

    async def send(message):
        pass

    async def receive():
        return {"type": "http.request"}

    scope = {"type": "http", "method": "GET", "path": "/crash"}
    with pytest.raises(ValueError, match="boom"):
        asyncio.run(middleware_cls(broken_app)(scope, receive, send))

    counter = stub.created[0]
    assert counter.events == [("inc", {"method": "GET", "path": "/crash",
                                       "status": "500"})]


def test_middleware_passes_through_non_http_scopes(monkeypatch):
    stub = _stub_prometheus(monkeypatch)
    middleware_cls = prometheus_mw.metrics_middleware()
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(middleware_cls(app)({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]
    assert stub.created[0].events == []  # nothing recorded


def test_metrics_endpoint_returns_exposition_text(monkeypatch):
    _stub_prometheus(monkeypatch)
    assert prometheus_mw.metrics_endpoint() == "# HELP stub\n"
