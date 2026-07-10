"""Single error envelope for the whole API."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def error_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    rid = request.headers.get("x-request-id", "-")
    return JSONResponse(status_code=exc.status,
                        content=error_body(exc.code, exc.message, rid))
