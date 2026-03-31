from __future__ import annotations

import json
from typing import Any

from core.errors import BackendError
from storage.base import ArtifactStorage


class S3ArtifactStorage(ArtifactStorage):
    def __init__(
        self,
        *,
        bucket: str,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise BackendError("boto3 is required for S3 storage support.") from exc

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    async def write_text(
        self,
        *,
        relative_path: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        extra = {"Metadata": {key: str(value) for key, value in (metadata or {}).items()}}
        self.client.put_object(
            Bucket=self.bucket,
            Key=relative_path,
            Body=content.encode("utf-8"),
            ContentType="text/plain",
            **extra,
        )
        return f"s3://{self.bucket}/{relative_path}"

    async def write_json(
        self,
        *,
        relative_path: str,
        payload: dict[str, Any] | list[Any],
    ) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=relative_path,
            Body=json.dumps(payload, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{self.bucket}/{relative_path}"

