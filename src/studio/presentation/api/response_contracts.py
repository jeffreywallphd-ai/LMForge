from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response


def success_response(data: Any, status_code: int = status.HTTP_200_OK) -> Response:
    return Response({"status": "success", "data": data}, status=status_code)


def error_response(
    message: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    code: str = "bad_request",
    details: Any | None = None,
) -> Response:
    payload: dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=status_code)


def validation_error_response(message: str, details: Any | None = None) -> Response:
    return error_response(
        message,
        status_code=status.HTTP_400_BAD_REQUEST,
        code="validation_error",
        details=details,
    )
