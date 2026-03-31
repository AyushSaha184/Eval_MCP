from __future__ import annotations

from fastapi import APIRouter

from db.session import session_scope
from domain.schemas import HistoryFilters
from services.datasets import DatasetService
from services.history import HistoryService
from services.projects import ProjectService
from services.prompts import PromptService


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects() -> dict:
    async with session_scope() as session:
        items = await ProjectService(session).list_projects()
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/datasets")
async def list_project_datasets(project: str) -> dict:
    async with session_scope() as session:
        items = await DatasetService(session).list_datasets(project)
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/prompts")
async def list_project_prompts(project: str) -> dict:
    async with session_scope() as session:
        items = await PromptService(session).list_prompts(project)
        return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{project}/history")
async def project_history(project: str, page: int = 1, page_size: int = 20) -> dict:
    async with session_scope() as session:
        result = await HistoryService(session).get_eval_history(
            HistoryFilters(project=project, page=page, page_size=page_size)
        )
        return result.model_dump(mode="json")

