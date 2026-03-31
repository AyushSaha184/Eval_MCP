from __future__ import annotations

from db.session import session_scope
from services.prompts import PromptService


async def list_prompts(project: str) -> dict:
    async with session_scope() as session:
        prompts = await PromptService(session).list_prompts(project)
        return {"ok": True, "items": [prompt.model_dump(mode="json") for prompt in prompts]}

