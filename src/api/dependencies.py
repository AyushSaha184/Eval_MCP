from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from core.config import get_settings


async def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    valid_keys = get_settings().valid_api_keys
    if not valid_keys:
        return

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    provided = x_api_key or bearer_token
    if provided and any(hmac.compare_digest(provided, expected) for expected in valid_keys):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": "Invalid API key.", "details": {}},
    )
