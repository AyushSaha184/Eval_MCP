from __future__ import annotations

from db.session import session_scope
from domain.schemas import BaselineSetRequest
from services.baselines import BaselineService


async def set_baseline_run(request: BaselineSetRequest) -> dict:
    async with session_scope() as session:
        run_id = await BaselineService(session).set_project_baseline(request.project, request.run_id)
        return {"ok": True, "project": request.project, "baseline_run_id": run_id}

