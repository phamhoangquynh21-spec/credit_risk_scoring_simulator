# infra/ — monitoring wiring (Stage 5.3)

Optional Prometheus + Grafana layer for the ML service. Nothing here is
required to run the app or the tests; `prometheus_client` is lazy-imported.

## 1. Install the optional extras

```bash
pip install -r infra/requirements-monitoring.txt
```

## 2. Wire the middleware + /metrics endpoint

`src/monitoring/prometheus_mw.py` is pure ASGI (no FastAPI import), so it
plugs into any ASGI app:

```python
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from src.monitoring.prometheus_mw import metrics_endpoint, metrics_middleware

app = FastAPI()
app.add_middleware(metrics_middleware())  # request count + latency histogram

@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics_endpoint())
```

Metrics exposed:

- `http_requests_total{method, status_class}` — request counter
- `http_request_duration_seconds{method}` — latency histogram

Labels are deliberately low-cardinality (method + status class only). The raw
request path is **not** a label: parameterized routes like
`/predictions/{uuid}` would otherwise create a new time series per id and blow
up Prometheus. Per-route breakdown needs the framework's route *template*
(e.g. Starlette's `request.scope["route"].path`), which is app-level
integration deferred to Stage 2 — add a `route` label there, never the raw
path.

Calling `metrics_middleware()` / `metrics_endpoint()` without
`prometheus_client` installed raises a RuntimeError pointing at
`infra/requirements-monitoring.txt`.

## 3. Prometheus scrape config

```yaml
scrape_configs:
  - job_name: credit-risk-ml
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets: ["<ml-service-host>:8000"]
```

## 4. Grafana dashboard

Import `infra/grafana-dashboard.json` (Dashboards → New → Import → Upload
JSON) and bind:

- `DS_PROMETHEUS` — your Prometheus datasource (request rate + p95 latency
  panels).
- `DS_POSTGRES` — a PostgreSQL datasource pointed at the Supabase database
  (drift panel; reads `monitoring_metrics` rows named `drift_psi.<feature>`
  written by `src/monitoring/drift.py`, thresholds warn 0.1 / alert 0.2).
