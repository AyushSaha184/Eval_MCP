from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RunAnnotation


class AnnotationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_id: str,
        label: str,
        note: str | None,
        created_by: str | None,
    ) -> RunAnnotation:
        annotation = RunAnnotation(
            run_id=run_id,
            label=label,
            note=note,
            created_by=created_by,
        )
        self.session.add(annotation)
        await self.session.flush()
        await self.session.refresh(annotation)
        return annotation

    async def list_by_run(self, run_db_id: str) -> list[RunAnnotation]:
        stmt = (
            select(RunAnnotation)
            .where(RunAnnotation.run_id == run_db_id)
            .order_by(desc(RunAnnotation.created_at))
        )
        return list((await self.session.execute(stmt)).scalars().all())

