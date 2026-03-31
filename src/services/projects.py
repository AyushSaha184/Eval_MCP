from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import ConflictError, NotFoundError
from db.repositories.projects import ProjectsRepository
from domain.schemas import ProjectCreate, ProjectRead


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "project"


def _to_project_read(project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        slug=project.slug,
        name=project.name,
        description=project.description,
        default_baseline_run_id=project.default_baseline_run_id,
        created_by=project.created_by,
        created_at=project.created_at,
    )


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectsRepository(session)

    async def create_project(self, request: ProjectCreate) -> ProjectRead:
        slug = request.slug or _slugify(request.name)
        existing = await self.projects.get_by_identifier(slug)
        if existing is not None and existing.slug == slug:
            raise ConflictError(f"Project slug `{slug}` already exists.")
        project = await self.projects.create(
            slug=slug,
            name=request.name,
            description=request.description,
            created_by=request.created_by,
        )
        return _to_project_read(project)

    async def get_project_model(self, identifier: str):
        project = await self.projects.get_by_identifier(identifier)
        if project is None:
            raise NotFoundError(f"Project `{identifier}` was not found.")
        return project

    async def get_project(self, identifier: str) -> ProjectRead:
        return _to_project_read(await self.get_project_model(identifier))

    async def list_projects(self) -> list[ProjectRead]:
        projects = await self.projects.list()
        return [_to_project_read(project) for project in projects]

