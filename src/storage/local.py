from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from storage.base import ArtifactStorage


class LocalArtifactStorage(ArtifactStorage):
    def __init__(self, root_directory: str) -> None:
        self.root = Path(root_directory)
        self.root.mkdir(parents=True, exist_ok=True)

    async def write_text(
        self,
        *,
        relative_path: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        if metadata:
            meta_target = target.with_suffix(target.suffix + ".meta.json")
            meta_target.write_text(json.dumps(metadata, default=str), encoding="utf-8")
        return target.as_posix()

    async def write_json(
        self,
        *,
        relative_path: str,
        payload: dict[str, Any] | list[Any],
    ) -> str:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
        return target.as_posix()

