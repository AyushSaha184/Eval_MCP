from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import EvalCaseResult, MetricResult
from db.queries import build_aggregate_metric_statement


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_case_result(self, **kwargs) -> EvalCaseResult:
        case_result = EvalCaseResult(**kwargs)
        self.session.add(case_result)
        await self.session.flush()
        await self.session.refresh(case_result)
        return case_result

    async def create_metric_results(self, rows: list[dict]) -> list[MetricResult]:
        metric_rows = [MetricResult(**row) for row in rows]
        self.session.add_all(metric_rows)
        await self.session.flush()
        return metric_rows

    async def get_aggregate_metrics(self, run_db_id: str) -> list[MetricResult]:
        return list((await self.session.execute(build_aggregate_metric_statement(run_db_id))).scalars().all())

    async def get_case_results(self, run_db_id: str) -> list[EvalCaseResult]:
        stmt = (
            select(EvalCaseResult)
            .where(EvalCaseResult.run_id == run_db_id)
            .order_by(EvalCaseResult.case_index.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_failed_case_results(self, run_db_id: str) -> list[EvalCaseResult]:
        stmt = (
            select(EvalCaseResult)
            .where(
                EvalCaseResult.run_id == run_db_id,
                EvalCaseResult.status.in_(("failed", "error")),
            )
            .order_by(EvalCaseResult.case_index.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_case_metrics(self, case_result_id: str) -> list[MetricResult]:
        stmt = (
            select(MetricResult)
            .where(MetricResult.case_result_id == case_result_id)
            .order_by(MetricResult.metric_name.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

