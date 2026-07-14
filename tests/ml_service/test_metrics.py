import importlib.util

import pytest
from fastapi.testclient import TestClient

from services.ml.main import create_app

_HAS_PROM = importlib.util.find_spec("prometheus_client") is not None


def test_app_builds_and_metrics_degrades_without_prometheus():
    # The app MUST start even when prometheus_client is missing; /metrics then
    # returns a clean 503 rather than crashing the service.
    c = TestClient(create_app())
    r = c.get("/metrics")
    if _HAS_PROM:
        assert r.status_code == 200
    else:
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "metrics_unavailable"


@pytest.mark.skipif(not _HAS_PROM, reason="prometheus_client not installed")
def test_metrics_exposition_when_available():
    c = TestClient(create_app())
    r = c.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
