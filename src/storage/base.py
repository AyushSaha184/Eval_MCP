from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ArtifactStorage(ABC):
    @abstractmethod
    async def write_text(
        self,
        *,
        relative_path: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def write_json(
        self,
        *,
        relative_path: str,
        payload: dict[str, Any] | list[Any],
    ) -> str:
        raise NotImplementedError

