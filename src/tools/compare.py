from __future__ import annotations

from db.session import session_scope
from domain.schemas import CompareRequest
from services.comparisons import ComparisonService


async def compare_prompt_versions(request: CompareRequest) -> dict:
    async with session_scope() as session:
        result = await ComparisonService(session).compare_prompt_versions(request)
        return {"ok": True, **result.model_dump(mode="json")}

