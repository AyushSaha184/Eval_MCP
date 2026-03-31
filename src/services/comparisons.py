from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from domain.enums import MetricDirection, RunStatus
from domain.schemas import CompareRequest, CompareResponse, MetricDelta, RunEvalRequest
from services.runs import RunService


def compute_metric_deltas(baseline_metrics: dict, candidate_metrics: dict) -> tuple[list[MetricDelta], list[str], list[str], list[str]]:
    deltas: list[MetricDelta] = []
    improved: list[str] = []
    regressed: list[str] = []
    unchanged: list[str] = []

    for metric_name in sorted(set(baseline_metrics) | set(candidate_metrics)):
        baseline_metric = baseline_metrics.get(metric_name)
        candidate_metric = candidate_metrics.get(metric_name)
        baseline_score = baseline_metric.score if baseline_metric else None
        candidate_score = candidate_metric.score if candidate_metric else None
        delta = None
        if baseline_score is not None and candidate_score is not None:
            delta = round(candidate_score - baseline_score, 6)
        direction = candidate_metric.direction if candidate_metric else baseline_metric.direction
        is_improved = delta is not None and (
            (direction == MetricDirection.HIGHER_IS_BETTER and delta > 0)
            or (direction == MetricDirection.LOWER_IS_BETTER and delta < 0)
        )
        is_regressed = delta is not None and (
            (direction == MetricDirection.HIGHER_IS_BETTER and delta < 0)
            or (direction == MetricDirection.LOWER_IS_BETTER and delta > 0)
        )
        deltas.append(
            MetricDelta(
                metric_name=metric_name,
                direction=direction,
                baseline_score=baseline_score,
                candidate_score=candidate_score,
                delta=delta,
                improved=is_improved,
                regressed=is_regressed,
            )
        )
        if is_improved:
            improved.append(metric_name)
        elif is_regressed:
            regressed.append(metric_name)
        else:
            unchanged.append(metric_name)
    return deltas, improved, regressed, unchanged


class ComparisonService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)
        self.metrics = MetricsRepository(session)
        self.run_service = RunService(session)

    async def compare_prompt_versions(self, request: CompareRequest) -> CompareResponse:
        baseline_run = await self.run_service.run_eval_suite(
            RunEvalRequest(
                project=request.project,
                prompt_reference=request.baseline_prompt_reference,
                dataset_reference=request.dataset_reference,
                metrics=request.metrics,
                model_config=request.model_settings,
                runtime_config=request.runtime_config,
                trigger_source=request.trigger_source,
                triggered_by=request.triggered_by,
                force_rerun=request.force_rerun,
            )
        )
        candidate_run = await self.run_service.run_eval_suite(
            RunEvalRequest(
                project=request.project,
                prompt_reference=request.candidate_prompt_reference,
                dataset_reference=request.dataset_reference,
                metrics=request.metrics,
                model_config=request.model_settings,
                runtime_config=request.runtime_config,
                trigger_source=request.trigger_source,
                triggered_by=request.triggered_by,
                force_rerun=request.force_rerun,
            )
        )
        baseline_model = await self.runs.get_by_public_id(baseline_run.run_id)
        candidate_model = await self.runs.get_by_public_id(candidate_run.run_id)
        if baseline_model.status != RunStatus.COMPLETED or candidate_model.status != RunStatus.COMPLETED:
            return CompareResponse(
                status="pending",
                baseline_run_id=baseline_model.run_id,
                candidate_run_id=candidate_model.run_id,
            )

        baseline_metrics = {
            metric.metric_name: metric
            for metric in await self.metrics.get_aggregate_metrics(baseline_model.id)
        }
        candidate_metrics = {
            metric.metric_name: metric
            for metric in await self.metrics.get_aggregate_metrics(candidate_model.id)
        }
        deltas, improved, regressed, unchanged = compute_metric_deltas(
            baseline_metrics,
            candidate_metrics,
        )

        return CompareResponse(
            status="completed",
            baseline_run_id=baseline_model.run_id,
            candidate_run_id=candidate_model.run_id,
            deltas=deltas,
            improved_metrics=improved,
            regressed_metrics=regressed,
            unchanged_metrics=unchanged,
        )
