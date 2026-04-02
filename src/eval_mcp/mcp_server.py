from __future__ import annotations

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
from eval_mcp.config import get_mcp_settings
from eval_mcp.tool_handlers import (
    annotate_run as annotate_run_tool,
    compare_prompt_versions as compare_prompt_versions_tool,
    detect_regression as detect_regression_tool,
    get_eval_history as get_eval_history_tool,
    get_latest_suggestion as get_latest_suggestion_tool,
    get_run_status as get_run_status_tool,
    get_supported_metrics as get_supported_metrics_tool,
    list_datasets as list_datasets_tool,
    list_projects as list_projects_tool,
    list_prompts as list_prompts_tool,
    register_golden_dataset as register_golden_dataset_tool,
    rerun_failed_cases as rerun_failed_cases_tool,
    run_eval_suite as run_eval_suite_tool,
    score_rag_pipeline as score_rag_pipeline_tool,
    set_baseline_run as set_baseline_run_tool,
    suggest_fix as suggest_fix_tool,
)
from tools.common import serialize_error

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - local compatibility shim
    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str) -> None:
            self.name = name
            self._tools: list[tuple[str | None, callable]] = []

        def tool(self, name: str | None = None):
            def decorator(func):
                self._tools.append((name or func.__name__, func))
                return func

            return decorator

        def run(self, *args, **kwargs) -> None:
            raise RuntimeError(
                "The `mcp` package is not installed. Install project dependencies to run the MCP server."
            )


def create_mcp_server() -> FastMCP:
    settings = get_mcp_settings()
    return FastMCP(settings.service_name)


mcp = create_mcp_server()


async def _invoke(handler, *args, **kwargs):
    try:
        return await handler(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - exercised through e2e tests
        return serialize_error(exc)


@mcp.tool(name="register_golden_dataset")
async def register_golden_dataset(request: DatasetRegistration) -> dict:
    return await _invoke(register_golden_dataset_tool, request)


@mcp.tool(name="run_eval_suite")
async def run_eval_suite(request: RunEvalRequest) -> dict:
    return await _invoke(run_eval_suite_tool, request)


@mcp.tool(name="compare_prompt_versions")
async def compare_prompt_versions(request: CompareRequest) -> dict:
    return await _invoke(compare_prompt_versions_tool, request)


@mcp.tool(name="detect_regression")
async def detect_regression(request: RegressionRequest) -> dict:
    return await _invoke(detect_regression_tool, request)


@mcp.tool(name="score_rag_pipeline")
async def score_rag_pipeline(request: RagScoreRequest) -> dict:
    return await _invoke(score_rag_pipeline_tool, request)


@mcp.tool(name="suggest_fix")
async def suggest_fix(request: SuggestFixRequest) -> dict:
    return await _invoke(suggest_fix_tool, request)


@mcp.tool(name="get_latest_suggestion")
async def get_latest_suggestion(run_id: str) -> dict:
    return await _invoke(get_latest_suggestion_tool, run_id)


@mcp.tool(name="get_eval_history")
async def get_eval_history(request: HistoryFilters) -> dict:
    return await _invoke(get_eval_history_tool, request)


@mcp.tool(name="get_run_status")
async def get_run_status(run_id: str) -> dict:
    return await _invoke(get_run_status_tool, run_id)


@mcp.tool(name="list_projects")
async def list_projects() -> dict:
    return await _invoke(list_projects_tool)


@mcp.tool(name="list_datasets")
async def list_datasets(project: str | None = None) -> dict:
    return await _invoke(list_datasets_tool, project)


@mcp.tool(name="list_prompts")
async def list_prompts(project: str | None = None) -> dict:
    return await _invoke(list_prompts_tool, project)


@mcp.tool(name="set_baseline_run")
async def set_baseline_run(request: BaselineSetRequest) -> dict:
    return await _invoke(set_baseline_run_tool, request)


@mcp.tool(name="rerun_failed_cases")
async def rerun_failed_cases(request: RerunFailedRequest) -> dict:
    return await _invoke(rerun_failed_cases_tool, request)


@mcp.tool(name="annotate_run")
async def annotate_run(request: AnnotationRequest) -> dict:
    return await _invoke(annotate_run_tool, request)


@mcp.tool(name="get_supported_metrics")
async def get_supported_metrics() -> dict:
    return await _invoke(get_supported_metrics_tool)


def run_server(*, dry_run: bool = False) -> None:
    if dry_run:
        create_mcp_server()
        return
    settings = get_mcp_settings()
    mcp.run(transport=settings.mcp_transport)
