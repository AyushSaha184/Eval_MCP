from __future__ import annotations

from db.session import session_scope
from domain.schemas import HistoryFilters
from services.history import HistoryService


async def get_eval_history(request: HistoryFilters) -> dict:
    async with session_scope() as session:
        history = await HistoryService(session).get_eval_history(request)
        return {"ok": True, **history.model_dump(mode="json")}

