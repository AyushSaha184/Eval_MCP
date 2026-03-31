from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import BaselineResolutionError, NotFoundError
from db.repositories.projects import ProjectsRepository
from db.repositories.runs import RunsRepository


class BaselineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectsRepository(session)
        self.runs = RunsRepository(session)

    async def set_project_baseline(self, project_identifier: str, run_public_id: str) -> str:
        project = await self.projects.get_by_identifier(project_identifier)
        if project is None:
            raise NotFoundError(f"Project `{project_identifier}` was not found.")
        run = await self.runs.get_by_public_id(run_public_id)
        if run is None or run.project_id != project.id:
            raise BaselineResolutionError("Baseline run does not belong to the target project.")
        await self.projects.set_default_baseline(project.id, run.id)
        return run.run_id

    async def get_project_baseline_run(self, project_identifier: str):
        project = await self.projects.get_by_identifier(project_identifier)
        if project is None:
            raise NotFoundError(f"Project `{project_identifier}` was not found.")
        if not project.default_baseline_run_id:
            raise BaselineResolutionError("Project does not have a default baseline run configured.")
        run = await self.runs.get_by_db_id(project.default_baseline_run_id)
        if run is None:
            raise BaselineResolutionError("Configured baseline run no longer exists.")
        return run

