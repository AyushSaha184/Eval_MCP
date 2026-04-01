from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import require_api_key
from db.session import session_scope
from domain.schemas import HistoryFilters
from services.auth import AuthContext, AuthService
from services.datasets import DatasetService
from services.history import HistoryService
from services.projects import ProjectService
from services.prompts import PromptService


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        if auth.is_legacy_admin:
            items = await ProjectService(session).list_projects()
        else:
            items = [await ProjectService(session).get_project(auth.project_id)]
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/datasets")
async def list_project_datasets(project: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, project)
        items = await DatasetService(session).list_datasets(project_model.id)
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/prompts")
async def list_project_prompts(project: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, project)
        items = await PromptService(session).list_prompts(project_model.id)
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/history")
async def project_history(
    project: str,
    page: int = 1,
    page_size: int = 20,
    auth: AuthContext = Depends(require_api_key),
) -> dict:
    async with session_scope() as session:
        project_model = await AuthService(session).authorize_project(auth, project)
        result = await HistoryService(session).get_eval_history(
            HistoryFilters(project=project_model.id, page=page, page_size=page_size)
        )
        return result.model_dump(mode="json")

