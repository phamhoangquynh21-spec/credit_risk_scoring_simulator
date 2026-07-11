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

    return app


app = create_app()
