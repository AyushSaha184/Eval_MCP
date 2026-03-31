from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core.config import Settings, get_settings
from core.logging import setup_logging


@lru_cache(maxsize=8)
def _get_engine_cached(database_url: str, log_level: str) -> AsyncEngine:
    setup_logging(log_level)
    engine_kwargs = {
        "future": True,
        "pool_pre_ping": True,
    }
    if database_url.endswith(":memory:") or "mode=memory" in database_url:
        engine_kwargs.update(
            {
                "connect_args": {"check_same_thread": False, "uri": True},
                "poolclass": StaticPool,
            }
        )
    return create_async_engine(
        database_url,
        **engine_kwargs,
    )


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved = settings or get_settings()
    return _get_engine_cached(resolved.database_url, resolved.log_level)


@lru_cache(maxsize=8)
def _get_session_factory_cached(database_url: str, log_level: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        _get_engine_cached(database_url, log_level),
        expire_on_commit=False,
        autoflush=False,
    )


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    resolved = settings or get_settings()
    return _get_session_factory_cached(resolved.database_url, resolved.log_level)


def clear_session_caches() -> None:
    _get_engine_cached.cache_clear()
    _get_session_factory_cached.cache_clear()


@asynccontextmanager
async def session_scope(settings: Settings | None = None):
    session_factory = get_session_factory(settings)
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
