from __future__ import annotations

import os
import shutil
import uuid

import pytest

from core.config import get_settings
from db.base import Base
import db.models  # noqa: F401
from db.session import clear_session_caches, get_engine, session_scope
from services.datasets import DatasetService
from services.projects import ProjectService
from services.prompts import PromptService
from services.runs import RunService
from services.status import StatusService
from tests.fixtures.sample_data import dataset_request, project_request, prompt_request, run_request
from workers.jobs import process_next_queued_run


def _reset_runtime_caches() -> None:
    get_settings.cache_clear()
    clear_session_caches()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("EVAL_MCP_SMOKE_DATABASE_URL"),
    reason="Set EVAL_MCP_SMOKE_DATABASE_URL to run live Postgres smoke coverage.",
)
async def test_live_postgres_smoke(monkeypatch) -> None:
    database_url = os.environ["EVAL_MCP_SMOKE_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LOCAL_ARTIFACT_DIRECTORY", ".test_tmp/live-artifacts")
    _reset_runtime_caches()

    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    unique_name = f"smoke-{uuid.uuid4().hex[:8]}"
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request(unique_name))
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="good prompt")
        )
        dataset = await DatasetService(session).register_dataset(dataset_request(project.slug, dataset_name="smoke_dataset"))
        queued = await RunService(session).run_eval_suite(run_request(project.slug, dataset.dataset_name, "qa"))

    await process_next_queued_run()

    async with session_scope() as session:
        status = await StatusService(session).get_run_status(queued.run_id)
        assert status.status == "completed"

    await engine.dispose()
    shutil.rmtree(".test_tmp", ignore_errors=True)
    _reset_runtime_caches()
