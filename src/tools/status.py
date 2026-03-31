from __future__ import annotations

from db.session import session_scope
from services.status import StatusService


async def get_run_status(run_id: str) -> dict:
    async with session_scope() as session:
        status = await StatusService(session).get_run_status(run_id)
        return {"ok": True, **status.model_dump(mode="json")}

