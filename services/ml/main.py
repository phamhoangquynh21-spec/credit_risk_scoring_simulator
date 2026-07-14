"""FastAPI app factory for the ML service."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .errors import AppError, app_error_handler, unhandled_error_handler, validation_error_handler
from .logging_config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Credit Risk ML Service", version="1.0.0")
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict:
        # Readiness = model bundle loadable + settings present.
        from .settings import settings
        from src import config
        return {
            "status": "ready" if config.MODEL_PATH.exists() else "not_ready",
            "model_present": config.MODEL_PATH.exists(),
            "supabase_configured": settings.configured,
        }

    from .routers import models
    app.include_router(models.router)

    from .routers import predict
    app.include_router(predict.router)

    from .routers import explain
    app.include_router(explain.router)

    from .routers import llm
    app.include_router(llm.router)

    from .routers import audit
    app.include_router(audit.router)

    _wire_metrics(app)

    return app


def _wire_metrics(app: FastAPI) -> None:
    """Wire Prometheus request metrics + a /metrics route. Optional: if
    prometheus_client is not installed the service still starts (degraded, no
    metrics) — a missing lib must never stop app startup on Render."""
    import logging

    log = logging.getLogger("ml_service")
    try:
        from src.monitoring.prometheus_mw import metrics_middleware
        app.add_middleware(metrics_middleware())
    except Exception as exc:  # prometheus_client missing / any wiring failure
        log.warning("prometheus metrics middleware disabled: %s", exc)

    @app.get("/metrics")
    def metrics():
        from fastapi.responses import Response

        from src.monitoring.prometheus_mw import metrics_endpoint
        try:
            return Response(content=metrics_endpoint(),
                            media_type="text/plain; version=0.0.4")
        except Exception as exc:  # prometheus_client not installed
            raise AppError("metrics_unavailable",
                           "metrics collection is not available", 503) from exc


app = create_app()
