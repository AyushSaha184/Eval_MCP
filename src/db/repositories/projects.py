from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Project


class ProjectsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        slug: str,
        name: str,
        description: str | None,
        created_by: str | None,
    ) -> Project:
        project = Project(
            slug=slug,
            name=name,
            description=description,
            created_by=created_by,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: str) -> Project | None:
        return await self.session.get(Project, project_id)

    async def get_by_identifier(self, identifier: str) -> Project | None:
        stmt = select(Project).where(
            or_(
                Project.id == identifier,
                Project.slug == identifier,
                Project.name == identifier,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[Project]:
        stmt = select(Project).order_by(Project.slug.asc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def set_default_baseline(self, project_id: str, run_db_id: str | None) -> None:
        project = await self.session.get(Project, project_id)
        if project is None:
            return
        project.default_baseline_run_id = run_db_id
        await self.session.flush()

