from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.errors import ValidationFailed
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
        if self.settings.storage_provider in {"s3", "b2"}:
            return S3ArtifactStorage(
                bucket=self.settings.object_storage_bucket or "",
                region=self.settings.object_storage_region,
                endpoint_url=self.settings.object_storage_endpoint_url,
                access_key_id=self.settings.object_storage_access_key_id,
                secret_access_key=self.settings.object_storage_access_key_secret,
            )
        return LocalArtifactStorage(self.settings.local_artifact_directory)

    @staticmethod
    def _build_relative_path(run_public_id: str, filename: str) -> str:
        safe_id = run_public_id.replace("\\", "/").strip("/")
        safe_filename = filename.replace("\\", "/").strip("/")
        if not safe_id or not safe_filename:
            raise ValidationFailed("Artifact path components cannot be empty.")
        combined = PurePosixPath(safe_id) / PurePosixPath(safe_filename)
        for part in combined.parts:
            if part in (".", "..") or "\x00" in part:
                raise ValidationFailed(
                    "Artifact path must not contain '.', '..', or null bytes."
                )
        path_str = str(combined)
        if path_str.startswith("/") or ".." in path_str.split("/"):
            raise ValidationFailed(
                "Artifact path must be relative and cannot escape base directory."
            )
        if len(path_str) > 500:
            raise ValidationFailed("Artifact path too long.")
        return path_str

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
        relative_path = self._build_relative_path(run_public_id, filename)
        uri = await storage.write_text(
            relative_path=relative_path, content=content, metadata=metadata
        )
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
        relative_path = self._build_relative_path(run_public_id, filename)
        uri = await storage.write_json(relative_path=relative_path, payload=payload)
        return await self.artifacts.create(
            run_id=run_db_id,
            artifact_type=artifact_type,
            storage_uri=uri,
            metadata_json=metadata or {},
        )
