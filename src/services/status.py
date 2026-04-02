from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError
from domain.enums import RunType
from db.repositories.runs import RunsRepository
from domain.schemas import RunStatusResponse
from services.suggestions import SuggestionService


class StatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)
        self.suggestions = SuggestionService(session)

    async def get_run_status(self, run_id: str) -> RunStatusResponse:
        run = await self.runs.get_by_public_id(run_id)
        if run is None:
            raise NotFoundError(f"Run `{run_id}` was not found.")

        latest_suggestion = None
        if run.run_type == RunType.SUGGESTION_EVAL:
            snapshot = await self.runs.get_snapshot(run.id)
            referenced_run_id = (
                (snapshot.runtime_config_snapshot_json or {}).get("referenced_run_id")
                if snapshot is not None
                else None
            )
            if referenced_run_id:
                latest_suggestion = await self.suggestions.get_latest_for_run(referenced_run_id)

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
            latest_suggestion=latest_suggestion,
        )

