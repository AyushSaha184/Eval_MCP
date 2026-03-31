from __future__ import annotations

import pytest

from db.session import session_scope
from domain.schemas import HistoryFilters
from services.projects import ProjectService
from services.prompts import PromptService
from tests.fixtures.sample_data import dataset_request, project_request, prompt_request, run_request
from tools.history import get_eval_history
from tools.register_dataset import register_golden_dataset
from tools.run_eval import run_eval_suite
from tools.status import get_run_status
from workers.jobs import process_next_queued_run


@pytest.mark.asyncio
async def test_tool_level_register_run_and_status_flow(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request("Tool Project"))
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="good prompt")
        )

    dataset_response = await register_golden_dataset(dataset_request(project.slug))
    run_response = await run_eval_suite(
        run_request(project.slug, dataset_response["dataset_name"], "qa")
    )
    queued_status = await get_run_status(run_response["run_id"])

    assert dataset_response["ok"] is True
    assert run_response["ok"] is True
    assert queued_status["status"] == "queued"

    await process_next_queued_run()

    completed_status = await get_run_status(run_response["run_id"])
    history = await get_eval_history(HistoryFilters(project=project.slug))

    assert completed_status["status"] == "completed"
    assert history["ok"] is True
    assert history["items"]
