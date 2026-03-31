from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.runs import RunsRepository
from domain.schemas import HistoryFilters, HistoryResponse, RunSummary
from services.projects import ProjectService


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.runs = RunsRepository(session)
        self.projects = ProjectService(session)

    async def get_eval_history(self, filters: HistoryFilters) -> HistoryResponse:
        project = await self.projects.get_project_model(filters.project)
        offset = (filters.page - 1) * filters.page_size
        rows = await self.runs.list_history(
            project_id=project.id,
            prompt_key=filters.prompt_key,
            dataset_name=filters.dataset_name,
            status=filters.status,
            label=filters.label,
            offset=offset,
            limit=filters.page_size,
        )
        total = await self.runs.count_history(
            project_id=project.id,
            prompt_key=filters.prompt_key,
            dataset_name=filters.dataset_name,
            status=filters.status,
            label=filters.label,
        )
        items = [
            RunSummary(
                run_id=row.EvalRun.run_id,
                project_slug=row.project_slug,
                run_type=row.EvalRun.run_type,
                status=row.EvalRun.status,
                prompt_key=row.prompt_key,
                prompt_version=row.prompt_version,
                dataset_name=row.dataset_name,
                dataset_version_hash=row.dataset_version_hash,
                metrics=row.EvalRun.metrics_requested_json,
                pass_rate=row.EvalRun.pass_rate,
                processed_cases=row.EvalRun.processed_cases,
                total_cases=row.EvalRun.total_cases,
                is_cached_result=row.EvalRun.is_cached_result,
                created_at=row.EvalRun.created_at,
                started_at=row.EvalRun.started_at,
                completed_at=row.EvalRun.completed_at,
                error_message=row.EvalRun.error_message,
            )
            for row in rows
        ]
        return HistoryResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
