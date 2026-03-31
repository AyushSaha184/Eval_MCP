from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Prompt


class PromptsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        prompt_key: str,
        version: int,
        content: str,
        system_prompt: str | None,
        metadata_json: dict,
        created_by: str | None,
    ) -> Prompt:
        prompt = Prompt(
            project_id=project_id,
            prompt_key=prompt_key,
            version=version,
            content=content,
            system_prompt=system_prompt,
            metadata_json=metadata_json,
            created_by=created_by,
        )
        self.session.add(prompt)
        await self.session.flush()
        await self.session.refresh(prompt)
        return prompt

    async def get_by_id(self, prompt_id: str) -> Prompt | None:
        return await self.session.get(Prompt, prompt_id)

    async def get_by_reference(
        self,
        *,
        project_id: str,
        prompt_id: str | None = None,
        prompt_key: str | None = None,
        version: int | None = None,
    ) -> Prompt | None:
        if prompt_id:
            stmt = select(Prompt).where(Prompt.id == prompt_id, Prompt.project_id == project_id)
            return (await self.session.execute(stmt)).scalar_one_or_none()

        if not prompt_key:
            return None

        stmt = select(Prompt).where(
            Prompt.project_id == project_id,
            Prompt.prompt_key == prompt_key,
        )
        if version is not None:
            stmt = stmt.where(Prompt.version == version)
        else:
            stmt = stmt.order_by(desc(Prompt.version)).limit(1)

        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_latest_version(self, *, project_id: str, prompt_key: str) -> int:
        stmt = select(func.max(Prompt.version)).where(
            Prompt.project_id == project_id,
            Prompt.prompt_key == prompt_key,
        )
        return (await self.session.execute(stmt)).scalar_one() or 0

    async def list_by_project(self, *, project_id: str) -> list[Prompt]:
        stmt = (
            select(Prompt)
            .where(Prompt.project_id == project_id)
            .order_by(Prompt.prompt_key.asc(), Prompt.version.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

