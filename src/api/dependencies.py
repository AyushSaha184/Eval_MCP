from __future__ import annotations

from fastapi import Header, HTTPException, status

from db.session import session_scope
from services.auth import AuthContext, AuthService


async def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AuthContext:
    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    provided = x_api_key or bearer_token
    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid API key.", "details": {}},
        )

    async with session_scope() as session:
        auth = await AuthService(session).resolve_api_key_context(provided)
    if auth is not None:
        return auth

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": "Invalid API key.", "details": {}},
    )
