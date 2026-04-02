from __future__ import annotations

from domain.schemas import (
    AnnotationRequest,
    CompareRequest,
    DatasetCaseInput,
    DatasetReference,
    DatasetRegistration,
    HistoryFilters,
    ModelConfig,
    ProjectCreate,
    PromptReference,
    PromptRegistration,
    RegressionRequest,
    RerunFailedRequest,
    RunEvalRequest,
    RuntimeConfig,
    SuggestFixRequest,
)


def project_request(name: str = "Demo Project") -> ProjectCreate:
    return ProjectCreate(name=name, created_by="tester")


def prompt_request(project: str, *, prompt_key: str, content: str, version: int | None = None) -> PromptRegistration:
    return PromptRegistration(
        project=project,
        prompt_key=prompt_key,
        version=version,
        content=content,
        created_by="tester",
    )


def dataset_request(project: str, dataset_name: str = "qa_dataset") -> DatasetRegistration:
    return DatasetRegistration(
        project=project,
        dataset_name=dataset_name,
        created_by="tester",
        cases=[
            DatasetCaseInput(
                input_text="What is 2 + 2?",
                expected_output="4",
                context=["Arithmetic basics"],
            ),
            DatasetCaseInput(
                input_text="Capital of France?",
                expected_output="Paris",
                context=["France has capital Paris"],
            ),
        ],
    )


def run_request(project: str, dataset_name: str, prompt_key: str, version: int | None = None) -> RunEvalRequest:
    return RunEvalRequest(
        project=project,
        prompt_reference=PromptReference(prompt_key=prompt_key, version=version),
        dataset_reference=DatasetReference(dataset_name=dataset_name),
        metrics=["answer_correctness", "exact_match"],
        model_config=ModelConfig(provider="stub", model_name="stub-evaluator"),
        runtime_config=RuntimeConfig(),
        triggered_by="tester",
    )


def compare_request(project: str, dataset_name: str, prompt_key: str) -> CompareRequest:
    return CompareRequest(
        project=project,
        baseline_prompt_reference=PromptReference(prompt_key=prompt_key, version=1),
        candidate_prompt_reference=PromptReference(prompt_key=prompt_key, version=2),
        dataset_reference=DatasetReference(dataset_name=dataset_name),
        metrics=["answer_correctness", "exact_match"],
        triggered_by="tester",
    )


def history_request(project: str) -> HistoryFilters:
    return HistoryFilters(project=project)


def regression_request(candidate_run_id: str, baseline_run_id: str | None = None, project: str | None = None) -> RegressionRequest:
    return RegressionRequest(candidate_run_id=candidate_run_id, baseline_run_id=baseline_run_id, project=project)


def rerun_request(run_id: str) -> RerunFailedRequest:
    return RerunFailedRequest(run_id=run_id, triggered_by="tester")


def annotation_request(run_id: str) -> AnnotationRequest:
    return AnnotationRequest(run_id=run_id, label="smoke", note="checked in tests", created_by="tester")


def suggestion_request(run_id: str) -> SuggestFixRequest:
    return SuggestFixRequest(run_id=run_id)

