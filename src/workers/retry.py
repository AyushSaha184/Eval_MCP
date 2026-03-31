from __future__ import annotations

import asyncio

from core.errors import BackendError


def is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, BackendError):
        text = str(exc).lower()
        return any(token in text for token in ("timeout", "rate limit", "temporar", "unavailable"))
    return False


async def run_with_retry(coro_factory, *, max_attempts: int = 2):
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except Exception as exc:  # pragma: no cover - exercised through integration
            last_error = exc
            if attempt >= max_attempts or not is_transient_error(exc):
                raise
            await asyncio.sleep(min(attempt, 3))
    if last_error is not None:
        raise last_error

