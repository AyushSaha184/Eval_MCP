from __future__ import annotations

from db.session import session_scope
from domain.schemas import SuggestFixRequest
from services.suggestions import SuggestionService


async def suggest_fix(request: SuggestFixRequest) -> dict:
    async with session_scope() as session:
        suggestion = await SuggestionService(session).suggest_fix(request)
        return {"ok": True, **suggestion.model_dump(mode="json")}

