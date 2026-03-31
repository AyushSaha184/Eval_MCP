from __future__ import annotations

from db.session import session_scope
from services.projects import ProjectService


async def list_projects() -> dict:
    async with session_scope() as session:
        projects = await ProjectService(session).list_projects()
        return {"ok": True, "items": [project.model_dump(mode="json") for project in projects]}

