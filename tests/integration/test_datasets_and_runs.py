from __future__ import annotations

import pytest

from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from db.session import session_scope
from domain.schemas import SuggestFixRequest
from eval_backends.base import JudgeSuggestionResult
from eval_backends.judges.google_judge import GoogleJudgeRunner
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


def _stub_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _generate_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str = "gemini-2.5-flash",
    ) -> JudgeSuggestionResult:
        return JudgeSuggestionResult(
            summary=f"Stub summary for {run_id}",
            suggestion_text="- Improve prompt grounding\n- Add stricter output format",
            metadata={"provider": "test-stub", "model_name": model_name},
        )

    monkeypatch.setattr(GoogleJudgeRunner, "generate_suggestion", _generate_suggestion)


@pytest.mark.asyncio
async def test_dataset_registration_and_run_snapshot_creation(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request())
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="good prompt")
        )
        dataset = await DatasetService(session).register_dataset(
            dataset_request(project.slug)
        )
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
async def test_worker_execution_history_and_suggestions(
    test_database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_judge(monkeypatch)

    async with session_scope() as session:
        project = await ProjectService(session).create_project(
            project_request("Execution Project")
        )
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(
            dataset_request(project.slug)
        )
        queued_run = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    processed_run_id = await process_next_queued_run()
    assert processed_run_id == queued_run.run_id

    async with session_scope() as session:
        status = await StatusService(session).get_run_status(queued_run.run_id)
        run_model = await RunsRepository(session).get_by_public_id(queued_run.run_id)
        aggregate_metrics = await MetricsRepository(session).get_aggregate_metrics(
            run_model.id
        )
        history = await HistoryService(session).get_eval_history(
            history_request(project.slug)
        )
        suggestion = await SuggestionService(session).suggest_fix(
            suggestion_request(queued_run.run_id)
        )

        assert status.status == "completed"
        assert aggregate_metrics
        assert history.items
        assert suggestion.run_id == queued_run.run_id
        assert suggestion.failure_clusters


@pytest.mark.asyncio
async def test_rerun_failed_cases_creates_subset_run(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(
            project_request("Rerun Project")
        )
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(
            dataset_request(project.slug)
        )
        original = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    await process_next_queued_run()

    async with session_scope() as session:
        rerun = await RunService(session).rerun_failed_cases(
            rerun_request(original.run_id)
        )
        rerun_model = await RunsRepository(session).get_by_public_id(rerun.run_id)
        snapshot = await RunsRepository(session).get_snapshot(rerun_model.id)

        assert rerun.status == "queued"
        assert snapshot.dataset_snapshot_json["selected_case_indices"]


@pytest.mark.asyncio
async def test_suggestion_eval_status_includes_latest_suggestion(
    test_database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_judge(monkeypatch)

    async with session_scope() as session:
        project = await ProjectService(session).create_project(
            project_request("Suggestion Status Project")
        )
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(
            dataset_request(project.slug)
        )
        eval_run = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    await process_next_queued_run()

    async with session_scope() as session:
        suggestion_run = await RunService(session).queue_suggestion(
            suggestion_request(eval_run.run_id)
        )

    processed_run_id = await process_next_queued_run()
    assert processed_run_id == suggestion_run.run_id

    async with session_scope() as session:
        status = await StatusService(session).get_run_status(
            suggestion_run.run_id, include_suggestion=True
        )
        assert status.run_type == "suggestion_eval"
        assert status.status == "completed"
        assert status.suggestion_summary is not None
        assert status.suggestion_summary.run_id == eval_run.run_id


@pytest.mark.asyncio
async def test_suggestion_queue_dedupes_for_implicit_and_explicit_default_model(
    test_database,
) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(
            project_request("Suggestion Cache Project")
        )
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt")
        )
        dataset = await DatasetService(session).register_dataset(
            dataset_request(project.slug)
        )
        eval_run = await RunService(session).run_eval_suite(
            run_request(project.slug, dataset.dataset_name, "qa")
        )

    queued_eval_run_id = await process_next_queued_run()
    assert queued_eval_run_id == eval_run.run_id

    async with session_scope() as session:
        first = await RunService(session).queue_suggestion(
            SuggestFixRequest(run_id=eval_run.run_id)
        )
        second = await RunService(session).queue_suggestion(
            SuggestFixRequest(run_id=eval_run.run_id, model_name="gemini-2.5-flash")
        )

    assert first.run_id == second.run_id
