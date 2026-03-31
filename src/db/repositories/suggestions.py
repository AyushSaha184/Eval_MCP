from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Suggestion


class SuggestionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_id: str,
        summary: str,
        suggestion_text: str,
        failure_clusters_json: list[dict],
        model_name: str,
        metadata_json: dict,
    ) -> Suggestion:
        suggestion = Suggestion(
            run_id=run_id,
            summary=summary,
            suggestion_text=suggestion_text,
            failure_clusters_json=failure_clusters_json,
            model_name=model_name,
            metadata_json=metadata_json,
        )
        self.session.add(suggestion)
        await self.session.flush()
        await self.session.refresh(suggestion)
        return suggestion

    async def list_by_run(self, run_db_id: str) -> list[Suggestion]:
        stmt = (
            select(Suggestion)
            .where(Suggestion.run_id == run_db_id)
            .order_by(desc(Suggestion.created_at))
        )
        return list((await self.session.execute(stmt)).scalars().all())

