from __future__ import annotations

import pytest

from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from db.session import session_scope
from services.datasets import DatasetService
from services.history import HistoryService
from services.projects import ProjectService
from services.prompts import PromptService
from services.runs import RunService
from services.suggestions import SuggestionService
from services.status import StatusService
from tests.fixtures.sample_data import (
    dataset_request,
    history_request,
    project_request,
    prompt_request,
    rerun_request,
    run_request,
    suggestion_request,
)
from workers.jobs import process_next_queued_run


@pytest.mark.asyncio
async def test_dataset_registration_and_run_snapshot_creation(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request())
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="good prompt")
        )
        dataset = await DatasetService(session).register_dataset(dataset_request(project.slug))
        queued_run = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )
        run_model = await RunsRepository(session).get_by_public_id(queued_run.run_id)
        snapshot = await RunsRepository(session).get_snapshot(run_model.id)

        assert dataset.case_count == 2
        assert queued_run.status == "queued"
        assert snapshot is not None
        assert snapshot.prompt_snapshot_json["prompt_key"] == "qa"
        assert snapshot.dataset_snapshot_json["version_hash"] == dataset.version_hash
        assert run_model.total_cases == 2


@pytest.mark.asyncio
async def test_worker_execution_history_and_suggestions(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request("Execution Project"))
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(dataset_request(project.slug))
        queued_run = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    processed_run_id = await process_next_queued_run()
    assert processed_run_id == queued_run.run_id

    async with session_scope() as session:
        status = await StatusService(session).get_run_status(queued_run.run_id)
        run_model = await RunsRepository(session).get_by_public_id(queued_run.run_id)
        aggregate_metrics = await MetricsRepository(session).get_aggregate_metrics(run_model.id)
        history = await HistoryService(session).get_eval_history(history_request(project.slug))
        suggestion = await SuggestionService(session).suggest_fix(suggestion_request(queued_run.run_id))

        assert status.status == "completed"
        assert aggregate_metrics
        assert history.items
        assert suggestion.run_id == queued_run.run_id
        assert suggestion.failure_clusters


@pytest.mark.asyncio
async def test_rerun_failed_cases_creates_subset_run(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request("Rerun Project"))
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(dataset_request(project.slug))
        original = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    await process_next_queued_run()

    async with session_scope() as session:
        rerun = await RunService(session).rerun_failed_cases(rerun_request(original.run_id))
        rerun_model = await RunsRepository(session).get_by_public_id(rerun.run_id)
        snapshot = await RunsRepository(session).get_snapshot(rerun_model.id)

        assert rerun.status == "queued"
        assert snapshot.dataset_snapshot_json["selected_case_indices"]

