from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from db.repositories.artifacts import ArtifactsRepository
from domain.enums import ArtifactType
from storage.local import LocalArtifactStorage
from storage.s3 import S3ArtifactStorage


class ArtifactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.artifacts = ArtifactsRepository(session)

    def _get_storage(self):
        if self.settings.storage_provider == "s3":
            return S3ArtifactStorage(
                bucket=self.settings.s3_bucket or "",
                region=self.settings.s3_region,
                endpoint_url=self.settings.s3_endpoint_url,
                access_key_id=self.settings.s3_access_key_id,
                secret_access_key=self.settings.s3_secret_access_key,
            )
        return LocalArtifactStorage(self.settings.local_artifact_directory)

    async def persist_text(
        self,
        *,
        run_db_id: str,
        run_public_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content: str,
        metadata: dict | None = None,
    ):
        storage = self._get_storage()
        relative_path = str(Path(run_public_id) / filename)
        uri = await storage.write_text(relative_path=relative_path, content=content, metadata=metadata)
        return await self.artifacts.create(
            run_id=run_db_id,
            artifact_type=artifact_type,
            storage_uri=uri,
            metadata_json=metadata or {},
        )

    async def persist_json(
        self,
        *,
        run_db_id: str,
        run_public_id: str,
        artifact_type: ArtifactType,
        filename: str,
        payload: dict | list,
        metadata: dict | None = None,
    ):
        storage = self._get_storage()
        relative_path = str(Path(run_public_id) / filename)
        uri = await storage.write_json(relative_path=relative_path, payload=payload)
        return await self.artifacts.create(
            run_id=run_db_id,
            artifact_type=artifact_type,
            storage_uri=uri,
            metadata_json=metadata or {},
        )

