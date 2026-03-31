from __future__ import annotations

from core.errors import EvalMCPError


def serialize_error(exc: Exception) -> dict:
    if isinstance(exc, EvalMCPError):
        return {
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        }
    return {
        "ok": False,
        "error": {
            "code": "unexpected_error",
            "message": str(exc),
            "details": {},
        },
    }

