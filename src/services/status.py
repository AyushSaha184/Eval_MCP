from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError
from db.repositories.runs import RunsRepository
from domain.schemas import RunStatusResponse


class StatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.runs = RunsRepository(session)

    async def get_run_status(self, run_id: str) -> RunStatusResponse:
        run = await self.runs.get_by_public_id(run_id)
        if run is None:
            raise NotFoundError(f"Run `{run_id}` was not found.")
        return RunStatusResponse(
            run_id=run.run_id,
            status=run.status,
            run_type=run.run_type,
            processed_cases=run.processed_cases,
            total_cases=run.total_cases,
            pass_rate=run.pass_rate,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            is_cached_result=run.is_cached_result,
        )

