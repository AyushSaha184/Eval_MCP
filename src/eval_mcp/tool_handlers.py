from __future__ import annotations

import asyncio
import logging
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
from eval_mcp.api_client import EvalMCPAPIClient, api_client, get_shared_client
from eval_mcp.config import get_mcp_settings
from eval_mcp.local_config import load_local_config

logger = logging.getLogger(__name__)

# FIX(concurrency): Limit the number of concurrent outbound API calls.
# Prevents resource exhaustion (OOM / CPU starvation) when many tool
# invocations arrive in parallel from an orchestrating agent.
_MAX_CONCURRENT_REQUESTS: int = 20
_request_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)


def _check_api_key() -> None:
    """Check if API key is configured, raise clear error if not."""
    settings = get_mcp_settings()
    local_cfg = load_local_config()
    if not settings.api_key and not local_cfg.get("api_key"):
        raise RuntimeError(
            "No API key configured. Either:\n"
            "  1. Run 'eval-mcp register --email <email> --password <pass>' to create an account\n"
            "  2. Run 'eval-mcp login --email <email> --password <pass>' to authenticate\n"
            "  3. Or set EVAL_MCP_API_KEY environment variable"
        )


async def _dispatch(
    method_name: str,
    payload: dict[str, Any] | None = None,
    *,
    client: EvalMCPAPIClient | None = None,
) -> dict:
    """Dispatch an API call through the shared (or injected) client.

    FIX(concurrency): All dispatches acquire the semaphore so at most
    ``_MAX_CONCURRENT_REQUESTS`` are in-flight simultaneously.

    FIX(connection pooling): When no explicit client is provided, the
    global shared client is used instead of creating a throwaway one.
    """
    if client is None:
        _check_api_key()

    dispatch_client = client
    if dispatch_client is None:
        # FIX(concurrency): Use the shared singleton instead of a per-call client.
        dispatch_client = await get_shared_client()

    async with _request_semaphore:
        method = getattr(dispatch_client, method_name)
        if not payload:
            return await method()
        if set(payload) <= {"run_id", "project"}:
            return await method(**payload)
        return await method(payload)


async def register_golden_dataset(
    request: DatasetRegistration, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "register_golden_dataset",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def run_eval_suite(
    request: RunEvalRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "run_eval_suite",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def compare_prompt_versions(
    request: CompareRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "compare_prompt_versions",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def detect_regression(
    request: RegressionRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "detect_regression",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def score_rag_pipeline(
    request: RagScoreRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "score_rag_pipeline",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def suggest_fix(
    request: SuggestFixRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "suggest_fix",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_latest_suggestion(
    run_id: str, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch("get_latest_suggestion", {"run_id": run_id}, client=client)


async def get_eval_history(
    request: HistoryFilters, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "get_eval_history",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_run_status(
    run_id: str, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch("get_run_status", {"run_id": run_id}, client=client)


async def list_projects(*, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch("list_projects", client=client)


def _resolve_project(project: str | None) -> str:
    if project:
        return project
    settings = get_mcp_settings()
    if settings.default_project:
        return settings.default_project
    raise ValueError(
        "A project must be provided or EVAL_MCP_DEFAULT_PROJECT must be set."
    )


async def list_datasets(
    project: str | None = None, *, client: EvalMCPAPIClient | None = None
) -> dict:
    resolved = _resolve_project(project)
    return await _dispatch("list_datasets", {"project": resolved}, client=client)


async def list_prompts(
    project: str | None = None, *, client: EvalMCPAPIClient | None = None
) -> dict:
    resolved = _resolve_project(project)
    return await _dispatch("list_prompts", {"project": resolved}, client=client)


async def set_baseline_run(
    request: BaselineSetRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "set_baseline_run",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def rerun_failed_cases(
    request: RerunFailedRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "rerun_failed_cases",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def annotate_run(
    request: AnnotationRequest, *, client: EvalMCPAPIClient | None = None
) -> dict:
    return await _dispatch(
        "annotate_run",
        request.model_dump(mode="json", by_alias=True, exclude_none=True),
        client=client,
    )


async def get_supported_metrics(*, client: EvalMCPAPIClient | None = None) -> dict:
    return await _dispatch("get_supported_metrics", client=client)
