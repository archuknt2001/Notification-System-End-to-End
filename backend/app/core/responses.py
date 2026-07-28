"""
Standardised API response envelope.

All API endpoints must return via these helpers so the frontend
can rely on a consistent { success, data, error, meta } shape.
"""

from typing import Any
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
    meta: dict | None = None,
) -> JSONResponse:
    body: dict = {"success": True, "message": message, "data": data}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(content=body, status_code=status_code)


def error_response(
    message: str,
    status_code: int = 400,
    errors: Any = None,
) -> JSONResponse:
    body: dict = {"success": False, "message": message}
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(content=body, status_code=status_code)
