from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Artifact


class ArtifactsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_id: str,
        artifact_type,
        storage_uri: str,
        metadata_json: dict,
    ) -> Artifact:
        artifact = Artifact(
            run_id=run_id,
            artifact_type=artifact_type,
            storage_uri=storage_uri,
            metadata_json=metadata_json,
        )
        self.session.add(artifact)
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def list_by_run(self, run_db_id: str) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.run_id == run_db_id)
            .order_by(desc(Artifact.created_at))
        )
        return list((await self.session.execute(stmt)).scalars().all())

