from __future__ import annotations

from core.config import get_settings
from core.metrics_registry import list_metric_definitions
from domain.enums import RunType
from domain.schemas import SupportedMetric, SupportedMetricsResponse


class CapabilityService:
    def get_supported_metrics(self) -> SupportedMetricsResponse:
        settings = get_settings()
        metrics = [
            SupportedMetric(
                name=metric.name,
                provider=metric.provider,
                family=metric.family,
                direction=metric.direction,
                default_threshold=metric.default_threshold,
                levels=list(metric.levels),
                description=metric.description,
            )
            for metric in list_metric_definitions()
        ]
        return SupportedMetricsResponse(
            metrics=metrics,
            run_types=[RunType.PROMPT_EVAL, RunType.RAG_EVAL, RunType.COMPARISON_BACKING_RUN],
            storage_provider=settings.storage_provider,
            queue_backend=settings.queue_backend,
        )

