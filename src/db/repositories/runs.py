from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import EvalCaseResult, EvalRun, RunAnnotation, RunSnapshot
from db.queries import build_history_statement
from domain.enums import CaseResultStatus, RunStatus, RunType


class RunsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_id: str,
        project_id: str,
        run_type: RunType,
        status: RunStatus,
        trigger_source: str,
        triggered_by: str | None,
        prompt_ref_id: str | None,
        dataset_ref_id: str | None,
        baseline_run_id: str | None,
        metrics_requested_json: list[str],
        cache_key: str,
        is_cached_result: bool,
        total_cases: int,
    ) -> EvalRun:
        run = EvalRun(
            run_id=run_id,
            project_id=project_id,
            run_type=run_type,
            status=status,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            prompt_ref_id=prompt_ref_id,
            dataset_ref_id=dataset_ref_id,
            baseline_run_id=baseline_run_id,
            metrics_requested_json=metrics_requested_json,
            cache_key=cache_key,
            is_cached_result=is_cached_result,
            total_cases=total_cases,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_snapshot(
        self,
        *,
        run_db_id: str,
        prompt_snapshot_json: dict,
        dataset_snapshot_json: dict,
        model_config_snapshot_json: dict,
        retriever_config_snapshot_json: dict,
        runtime_config_snapshot_json: dict,
    ) -> RunSnapshot:
        snapshot = RunSnapshot(
            run_id=run_db_id,
            prompt_snapshot_json=prompt_snapshot_json,
            dataset_snapshot_json=dataset_snapshot_json,
            model_config_snapshot_json=model_config_snapshot_json,
            retriever_config_snapshot_json=retriever_config_snapshot_json,
            runtime_config_snapshot_json=runtime_config_snapshot_json,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_by_public_id(self, run_id: str) -> EvalRun | None:
        stmt = select(EvalRun).where(EvalRun.run_id == run_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_db_id(self, run_db_id: str) -> EvalRun | None:
        return await self.session.get(EvalRun, run_db_id)

    async def get_snapshot(self, run_db_id: str) -> RunSnapshot | None:
        stmt = select(RunSnapshot).where(RunSnapshot.run_id == run_db_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_cached_completed(
        self,
        *,
        project_id: str,
        cache_key: str,
        run_type: RunType,
    ) -> EvalRun | None:
        stmt = (
            select(EvalRun)
            .where(
                EvalRun.project_id == project_id,
                EvalRun.cache_key == cache_key,
                EvalRun.run_type == run_type,
                EvalRun.status == RunStatus.COMPLETED,
            )
            .order_by(EvalRun.completed_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_cached_inflight(
        self,
        *,
        project_id: str,
        cache_key: str,
        run_type: RunType,
    ) -> EvalRun | None:
        stmt = (
            select(EvalRun)
            .where(
                EvalRun.project_id == project_id,
                EvalRun.cache_key == cache_key,
                EvalRun.run_type == run_type,
                EvalRun.status.in_((RunStatus.QUEUED, RunStatus.RUNNING)),
            )
            .order_by(EvalRun.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_history(
        self,
        *,
        project_id: str,
        prompt_key: str | None = None,
        dataset_name: str | None = None,
        status: RunStatus | None = None,
        label: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ):
        stmt = build_history_statement(project_id)
        if prompt_key is not None:
            stmt = stmt.where(stmt.selected_columns.prompt_key == prompt_key)
        if dataset_name is not None:
            stmt = stmt.where(stmt.selected_columns.dataset_name == dataset_name)
        if status is not None:
            stmt = stmt.where(EvalRun.status == status)
        if label is not None:
            stmt = stmt.join(RunAnnotation, RunAnnotation.run_id == EvalRun.id).where(
                RunAnnotation.label == label
            )
        stmt = stmt.offset(offset).limit(limit)
        return (await self.session.execute(stmt)).all()

    async def count_history(
        self,
        *,
        project_id: str,
        prompt_key: str | None = None,
        dataset_name: str | None = None,
        status: RunStatus | None = None,
        label: str | None = None,
    ) -> int:
        stmt = select(func.count(EvalRun.id)).where(EvalRun.project_id == project_id)
        if prompt_key is not None:
            stmt = stmt.join(EvalRun.prompt_ref).where(
                EvalRun.prompt_ref.has(prompt_key=prompt_key)
            )
        if dataset_name is not None:
            stmt = stmt.join(EvalRun.dataset_ref).where(
                EvalRun.dataset_ref.has(dataset_name=dataset_name)
            )
        if status is not None:
            stmt = stmt.where(EvalRun.status == status)
        if label is not None:
            stmt = stmt.join(RunAnnotation, RunAnnotation.run_id == EvalRun.id).where(
                RunAnnotation.label == label
            )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def mark_running(
        self, run_db_id: str, attempt_count: int | None = None
    ) -> None:
        run = await self.get_by_db_id(run_db_id)
        if run is None:
            return
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.last_heartbeat_at = run.started_at
        if attempt_count is not None:
            run.attempt_count = attempt_count
        await self.session.flush()

    async def update_progress(
        self,
        *,
        run_db_id: str,
        processed_cases: int,
        total_cases: int | None = None,
    ) -> None:
        run = await self.get_by_db_id(run_db_id)
        if run is None:
            return
        run.processed_cases = processed_cases
        if total_cases is not None:
            run.total_cases = total_cases
        run.last_heartbeat_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def finalize_success(
        self,
        *,
        run_db_id: str,
        pass_rate: float,
        processed_cases: int,
        total_cases: int,
    ) -> None:
        run = await self.get_by_db_id(run_db_id)
        if run is None:
            return
        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        run.processed_cases = processed_cases
        run.total_cases = total_cases
        run.pass_rate = pass_rate
        run.error_message = None
        run.last_heartbeat_at = run.completed_at
        await self.session.flush()

    async def finalize_failure(
        self,
        *,
        run_db_id: str,
        error_message: str,
        processed_cases: int | None = None,
    ) -> None:
        run = await self.get_by_db_id(run_db_id)
        if run is None:
            return
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_message
        if processed_cases is not None:
            run.processed_cases = processed_cases
        run.last_heartbeat_at = run.completed_at
        await self.session.flush()

    async def claim_next_queued_run(self) -> EvalRun | None:
        stmt = (
            select(EvalRun)
            .where(EvalRun.status == RunStatus.QUEUED)
            .order_by(EvalRun.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        run = (await self.session.execute(stmt)).scalar_one_or_none()
        if run is None:
            return None
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.last_heartbeat_at = run.started_at
        run.attempt_count += 1
        await self.session.flush()
        return run

    async def claim_queued_run_by_public_id(self, run_id: str) -> EvalRun | None:
        stmt = (
            select(EvalRun)
            .where(
                EvalRun.run_id == run_id,
                EvalRun.status == RunStatus.QUEUED,
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        run = (await self.session.execute(stmt)).scalar_one_or_none()
        if run is None:
            return None
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.last_heartbeat_at = run.started_at
        run.attempt_count += 1
        await self.session.flush()
        return run

    async def get_failed_case_indices(self, run_db_id: str) -> list[int]:
        stmt = (
            select(EvalCaseResult.case_index)
            .where(
                EvalCaseResult.run_id == run_db_id,
                EvalCaseResult.status == CaseResultStatus.FAILED,
            )
            .order_by(EvalCaseResult.case_index.asc())
        )
        return [row[0] for row in (await self.session.execute(stmt)).all()]
