from __future__ import annotations

from db.session import session_scope
from domain.schemas import RegressionRequest
from services.regressions import RegressionService


async def detect_regression(request: RegressionRequest) -> dict:
    async with session_scope() as session:
        result = await RegressionService(session).detect_regression(request)
        return {"ok": True, **result.model_dump(mode="json")}

