from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import require_api_key
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
from services.auth import AuthContext, AuthService
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
async def list_projects(auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        if auth.is_legacy_admin:
            items = await ProjectService(session).list_projects()
        else:
            items = [await ProjectService(session).get_project(auth.project_id)]
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.get("/projects/{project}/datasets")
async def list_project_datasets(project: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, project)
        items = await DatasetService(session).list_datasets(project_model.id)
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.get("/projects/{project}/prompts")
async def list_project_prompts(project: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, project)
        items = await PromptService(session).list_prompts(project_model.id)
        return {"ok": True, "items": [item.model_dump(mode="json") for item in items]}


@router.post("/datasets/register")
async def register_dataset(request: DatasetRegistration, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        dataset = await DatasetService(session).register_dataset(request.model_copy(update={"project": project_model.id}))
        return {
            "ok": True,
            "dataset_name": dataset.dataset_name,
            "version_hash": dataset.version_hash,
            "case_count": dataset.case_count,
        }


@router.post("/runs/eval")
async def run_eval(request: RunEvalRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        run = await RunService(session).run_eval_suite(request.model_copy(update={"project": project_model.id}))
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }


@router.post("/runs/rag")
async def run_rag_eval(request: RagScoreRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        run = await RunService(session).score_rag_pipeline(request.model_copy(update={"project": project_model.id}))
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }


@router.get("/runs/{run_id}/status")
async def get_run_status(run_id: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        await AuthService(session).authorize_run(auth, run_id)
        result = await StatusService(session).get_run_status(run_id)
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/history/query")
async def query_history(request: HistoryFilters, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        result = await HistoryService(session).get_eval_history(request.model_copy(update={"project": project_model.id}))
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/baselines/set")
async def set_baseline(request: BaselineSetRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        await AuthService(session).authorize_run(auth, request.run_id)
        run_id = await BaselineService(session).set_project_baseline(project_model.id, request.run_id)
        return {"ok": True, "project": project_model.slug, "baseline_run_id": run_id}


@router.post("/comparisons/prompt-versions")
async def compare_prompt_versions(request: CompareRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, request.project)
        result = await ComparisonService(session).compare_prompt_versions(
            request.model_copy(update={"project": project_model.id})
        )
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/regressions/detect")
async def detect_regression(request: RegressionRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        auth_service = AuthService(session)
        await auth_service.authorize_run(auth, request.candidate_run_id)
        if request.baseline_run_id:
            await auth_service.authorize_run(auth, request.baseline_run_id)
        effective_project = request.project
        if effective_project is not None:
            project_model = await auth_service.authorize_project(auth, effective_project)
            effective_project = project_model.id
        result = await RegressionService(session).detect_regression(
            request.model_copy(update={"project": effective_project})
        )
        return {"ok": True, **result.model_dump(mode="json")}


@router.post("/runs/rerun-failed")
async def rerun_failed(request: RerunFailedRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        await AuthService(session).authorize_run(auth, request.run_id)
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
async def annotate_run(request: AnnotationRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        await AuthService(session).authorize_run(auth, request.run_id)
        annotation = await RunService(session).annotate_run(request)
        return {"ok": True, **annotation.model_dump(mode="json")}


@router.post("/suggestions")
async def suggest_fix(request: SuggestFixRequest, auth: AuthContext = Depends(require_api_key)) -> dict:
    """Queue a suggestion evaluation run.
    
    Returns immediately with a run_id for polling status, rather than
    blocking on LLM judge evaluation.
    """
    async with session_scope() as session:
        await AuthService(session).authorize_run(auth, request.run_id)
        queued = await RunService(session).queue_suggestion(request)
        return {"ok": True, **queued.model_dump(mode="json")}


@router.get("/runs/{run_id}/suggestions/latest")
async def get_latest_suggestion(run_id: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        await AuthService(session).authorize_run(auth, run_id)
        suggestion = await SuggestionService(session).get_latest_for_run(run_id)
        if suggestion is None:
            return {"ok": True, "status": "pending", "suggestion": None}
        return {"ok": True, "status": "completed", **suggestion.model_dump(mode="json")}


@router.get("/meta/supported-metrics")
async def supported_metrics() -> dict:
    return {"ok": True, **CapabilityService().get_supported_metrics().model_dump(mode="json")}
