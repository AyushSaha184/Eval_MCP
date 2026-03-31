from __future__ import annotations

from db.session import session_scope
from domain.schemas import RerunFailedRequest
from services.runs import RunService


async def rerun_failed_cases(request: RerunFailedRequest) -> dict:
    async with session_scope() as session:
        run = await RunService(session).rerun_failed_cases(request)
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }

