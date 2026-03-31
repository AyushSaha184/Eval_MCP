from __future__ import annotations

from fastapi import APIRouter

from db.session import session_scope
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
from services.baselines import BaselineService
from services.capabilities import CapabilityService
from services.comparisons import ComparisonService
from services.datasets import DatasetService
from services.history import HistoryService
from services.projects import ProjectService
from services.prompts import PromptService
from services.regressions import RegressionService
from services.runs import RunService
from services.status import StatusService
from services.suggestions import SuggestionService


router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/projects")
async def list_projects() -> dict:
    async with session_scope() as session:
        items = await ProjectService(session).list_projects()
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.get("/projects/{project}/datasets")
async def list_project_datasets(project: str) -> dict:
    async with session_scope() as session:
        items = await DatasetService(session).list_datasets(project)
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.get("/projects/{project}/prompts")
async def list_project_prompts(project: str) -> dict:
    async with session_scope() as session:
        items = await PromptService(session).list_prompts(project)
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.post("/datasets/register")
async def register_dataset(request: DatasetRegistration) -> dict:
    async with session_scope() as session:
        dataset = await DatasetService(session).register_dataset(request)
        return {
            "ok": True,
            "dataset_name": dataset.dataset_name,
            "version_hash": dataset.version_hash,
            "case_count": dataset.case_count,
        }


@router.post("/runs/eval")
async def run_eval(request: RunEvalRequest) -> dict:
    async with session_scope() as session:
        run = await RunService(session).run_eval_suite(request)
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }


@router.post("/runs/rag")
async def run_rag_eval(request: RagScoreRequest) -> dict:
    async with session_scope() as session:
        run = await RunService(session).score_rag_pipeline(request)
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }


@router.get("/runs/{run_id}/status")
async def get_run_status(run_id: str) -> dict:
    async with session_scope() as session:
        result = await StatusService(session).get_run_status(run_id)
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/history/query")
async def query_history(request: HistoryFilters) -> dict:
    async with session_scope() as session:
        result = await HistoryService(session).get_eval_history(request)
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/baselines/set")
async def set_baseline(request: BaselineSetRequest) -> dict:
    async with session_scope() as session:
        run_id = await BaselineService(session).set_project_baseline(request.project, request.run_id)
        return {"ok": True, "project": request.project, "baseline_run_id": run_id}


@router.post("/comparisons/prompt-versions")
async def compare_prompt_versions(request: CompareRequest) -> dict:
    async with session_scope() as session:
        result = await ComparisonService(session).compare_prompt_versions(request)
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/regressions/detect")
async def detect_regression(request: RegressionRequest) -> dict:
    async with session_scope() as session:
        result = await RegressionService(session).detect_regression(request)
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/runs/rerun-failed")
async def rerun_failed(request: RerunFailedRequest) -> dict:
    async with session_scope() as session:
        run = await RunService(session).rerun_failed_cases(request)
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }


@router.post("/runs/annotate")
async def annotate_run(request: AnnotationRequest) -> dict:
    async with session_scope() as session:
        annotation = await RunService(session).annotate_run(request)
        return {"ok": True, **annotation.model_dump(mode="json")}


@router.post("/suggestions")
async def suggest_fix(request: SuggestFixRequest) -> dict:
    async with session_scope() as session:
        result = await SuggestionService(session).suggest_fix(request)
        return {"ok": True, **result.model_dump(mode="json")}


@router.get("/meta/supported-metrics")
async def supported_metrics() -> dict:
    return {"ok": True, **CapabilityService().get_supported_metrics().model_dump(mode="json")}
