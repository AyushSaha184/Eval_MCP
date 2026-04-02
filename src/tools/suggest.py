from __future__ import annotations

from db.session import session_scope
from domain.schemas import SuggestFixRequest
from services.runs import RunService


async def suggest_fix(request: SuggestFixRequest) -> dict:
    async with session_scope() as session:
        queued = await RunService(session).queue_suggestion(request)
        return {"ok": True, **queued.model_dump(mode="json")}

