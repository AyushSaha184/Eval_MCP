from __future__ import annotations

import sys
from pathlib import Path
import shutil
import uuid

import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import get_settings
from db.base import Base
import db.models  # noqa: F401
from db.session import clear_session_caches, get_engine


def _reset_runtime_caches() -> None:
    get_settings.cache_clear()
    clear_session_caches()


@pytest_asyncio.fixture
async def test_database(monkeypatch):
    artifacts_dir = ".test_tmp/artifacts"
    memory_name = f"file:eval_mcp_{uuid.uuid4().hex}?mode=memory&cache=shared"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{memory_name}")
    monkeypatch.setenv("LOCAL_ARTIFACT_DIRECTORY", artifacts_dir)
    _reset_runtime_caches()
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield "sqlite-memory"
    await engine.dispose()
    shutil.rmtree(".test_tmp", ignore_errors=True)
    _reset_runtime_caches()
