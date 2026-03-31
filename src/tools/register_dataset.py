from __future__ import annotations

from db.session import session_scope
from domain.schemas import DatasetRegistration
from services.datasets import DatasetService


async def register_golden_dataset(request: DatasetRegistration) -> dict:
    async with session_scope() as session:
        dataset = await DatasetService(session).register_dataset(request)
        return {
            "ok": True,
            "dataset_name": dataset.dataset_name,
            "version_hash": dataset.version_hash,
            "case_count": dataset.case_count,
        }

