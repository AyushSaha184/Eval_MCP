from __future__ import annotations

import pytest

from db.session import session_scope
from services.baselines import BaselineService
from services.comparisons import ComparisonService
from services.datasets import DatasetService
from services.projects import ProjectService
from services.prompts import PromptService
from services.regressions import RegressionService
from tests.fixtures.sample_data import compare_request, dataset_request, project_request, prompt_request, regression_request
from workers.jobs import process_next_queued_run


@pytest.mark.asyncio
async def test_comparison_flow_and_baseline_regression(test_database) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(project_request("Compare Project"))
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="bad prompt", version=1)
        )
        await PromptService(session).register_prompt(
            prompt_request(project.slug, prompt_key="qa", content="good prompt", version=2)
        )
        dataset = await DatasetService(session).register_dataset(dataset_request(project.slug))
        first_response = await ComparisonService(session).compare_prompt_versions(
            compare_request(project.slug, dataset.dataset_name, "qa")
        )

        assert first_response.status == "pending"

    await process_next_queued_run()
    await process_next_queued_run()

    async with session_scope() as session:
        comparison = await ComparisonService(session).compare_prompt_versions(
            compare_request(project.slug, dataset.dataset_name, "qa")
        )
        await BaselineService(session).set_project_baseline(project.slug, comparison.candidate_run_id)
        regression = await RegressionService(session).detect_regression(
            regression_request(
                candidate_run_id=comparison.baseline_run_id,
                project=project.slug,
            )
        )

        assert comparison.status == "completed"
        assert "answer_correctness" in comparison.improved_metrics
        assert regression.is_regression is True

