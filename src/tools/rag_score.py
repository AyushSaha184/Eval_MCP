from __future__ import annotations

from db.session import session_scope
from domain.schemas import RagScoreRequest
from services.runs import RunService


async def score_rag_pipeline(request: RagScoreRequest) -> dict:
    async with session_scope() as session:
        run = await RunService(session).score_rag_pipeline(request)
        return {
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "cached": run.cached,
            "cache_key": run.cache_key,
            "source_run_id": run.source_run_id,
        }

