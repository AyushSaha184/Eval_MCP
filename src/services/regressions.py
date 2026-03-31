from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import BaselineResolutionError, NotFoundError
from core.metrics_registry import get_metric_definition
from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from domain.enums import MetricDirection
from domain.schemas import RegressionMetricOutcome, RegressionRequest, RegressionResponse
from services.baselines import BaselineService


def is_metric_regression(
    *,
    direction: MetricDirection,
    baseline_score: float,
    candidate_score: float,
    allowed_delta: float,
) -> bool:
    if direction == MetricDirection.HIGHER_IS_BETTER:
        return candidate_score < (baseline_score - allowed_delta)
    return candidate_score > (baseline_score + allowed_delta)


class RegressionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)
        self.metrics = MetricsRepository(session)
        self.baselines = BaselineService(session)

    async def detect_regression(self, request: RegressionRequest) -> RegressionResponse:
        candidate_run = await self.runs.get_by_public_id(request.candidate_run_id)
        if candidate_run is None:
            raise NotFoundError(f"Run `{request.candidate_run_id}` was not found.")

        if request.baseline_run_id:
            baseline_run = await self.runs.get_by_public_id(request.baseline_run_id)
            if baseline_run is None:
                raise NotFoundError(f"Baseline run `{request.baseline_run_id}` was not found.")
        else:
            baseline_run = await self.baselines.get_project_baseline_run(
                request.project or candidate_run.project_id
            )

        if baseline_run.project_id != candidate_run.project_id:
            raise BaselineResolutionError("Baseline and candidate runs must belong to the same project.")

        overrides = {item.metric_name: item.allowed_delta for item in request.thresholds}
        baseline_metrics = {
            metric.metric_name: metric
            for metric in await self.metrics.get_aggregate_metrics(baseline_run.id)
        }
        candidate_metrics = {
            metric.metric_name: metric
            for metric in await self.metrics.get_aggregate_metrics(candidate_run.id)
        }
        outcomes: list[RegressionMetricOutcome] = []
        is_regression = False

        for metric_name in sorted(set(baseline_metrics) | set(candidate_metrics)):
            baseline_metric = baseline_metrics.get(metric_name)
            candidate_metric = candidate_metrics.get(metric_name)
            if baseline_metric is None or candidate_metric is None:
                continue
            allowed_delta = overrides.get(metric_name, 0.0)
            delta = round(candidate_metric.score - baseline_metric.score, 6)
            definition = get_metric_definition(metric_name)
            regressed = is_metric_regression(
                direction=definition.direction,
                baseline_score=baseline_metric.score,
                candidate_score=candidate_metric.score,
                allowed_delta=allowed_delta,
            )
            is_regression = is_regression or regressed
            outcomes.append(
                RegressionMetricOutcome(
                    metric_name=metric_name,
                    baseline_score=baseline_metric.score,
                    candidate_score=candidate_metric.score,
                    delta=delta,
                    direction=definition.direction,
                    allowed_delta=allowed_delta,
                    regressed=regressed,
                )
            )

        return RegressionResponse(
            baseline_run_id=baseline_run.run_id,
            candidate_run_id=candidate_run.run_id,
            is_regression=is_regression,
            affected_metrics=[outcome for outcome in outcomes if outcome.regressed],
        )
