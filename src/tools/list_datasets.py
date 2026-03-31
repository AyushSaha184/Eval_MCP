from __future__ import annotations

from db.session import session_scope
from services.datasets import DatasetService


async def list_datasets(project: str) -> dict:
    async with session_scope() as session:
        datasets = await DatasetService(session).list_datasets(project)
        return {"ok": True, "items": [dataset.model_dump(mode="json") for dataset in datasets]}

