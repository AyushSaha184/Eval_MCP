from __future__ import annotations

from typing import Any

from domain.schemas import (
    AnnotationRequest,
    BaselineSetRequest,
    CompareRequest,
    DatasetRegistration,
    HistoryFilters,
    RagScoreRequest,
    RegressionRequest,
    RerunFailedRequest,
    RunEvalRequest,
    SuggestFixRequest,
)
from eval_mcp.api_client import EvalMCPAPIClient, api_client
from eval_mcp.config import get_mcp_settings


async def _dispatch(
    method_name: str,
    payload: dict[str, Any] | None = None,
    *,
    client: EvalMCPAPIClient | None = None,
) -> dict:
    dispatch_client = client
    if dispatch_client is None:
        async with api_client() as default_client:
            return await _dispatch(method_name, payload, client=default_client)

    method = getattr(dispatch_client, method_name)
    if not payload:
        return await method()
    if set(payload) <= {"run_id", "project"}:
        return await method(**payload)
    return await method(payload)


async def register_golden_dataset(request: DatasetRegistration, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "register_golden_dataset",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def run_eval_suite(request: RunEvalRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "run_eval_suite",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def compare_prompt_versions(request: CompareRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "compare_prompt_versions",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def detect_regression(request: RegressionRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "detect_regression",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def score_rag_pipeline(request: RagScoreRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "score_rag_pipeline",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def suggest_fix(request: SuggestFixRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "suggest_fix",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_eval_history(request: HistoryFilters, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "get_eval_history",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_run_status(run_id: str, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch("get_run_status", {"run_id": run_id}, client=client)


async def list_projects(*, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch("list_projects", client=client)


def _resolve_project(project: str | None) -> str:
    if project:
        return project
    settings = get_mcp_settings()
    if settings.default_project:
        return settings.default_project
    raise ValueError("A project must be provided or EVAL_MCP_DEFAULT_PROJECT must be set.")


async def list_datasets(project: str | None = None, *, client: EvalMCPAPIClient | None = None) -> dict:
    resolved = _resolve_project(project)
    return await _dispatch("list_datasets", {"project": resolved}, client=client)


async def list_prompts(project: str | None = None, *, client: EvalMCPAPIClient | None = None) -> dict:
    resolved = _resolve_project(project)
    return await _dispatch("list_prompts", {"project": resolved}, client=client)


async def set_baseline_run(request: BaselineSetRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "set_baseline_run",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def rerun_failed_cases(request: RerunFailedRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "rerun_failed_cases",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def annotate_run(request: AnnotationRequest, *, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch(
        "annotate_run",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_supported_metrics(*, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch("get_supported_metrics", client=client)
