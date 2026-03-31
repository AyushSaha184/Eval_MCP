from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from domain.enums import MetricDirection


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    provider: str
    family: str
    direction: MetricDirection
    default_threshold: float | None
    levels: tuple[str, ...]
    description: str | None = None


_METRICS: dict[str, MetricDefinition] = {
    "exact_match": MetricDefinition(
        name="exact_match",
        provider="internal",
        family="correctness",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=1.0,
        levels=("case", "aggregate"),
        description="Exact normalized string equality between actual and expected outputs.",
    ),
    "answer_correctness": MetricDefinition(
        name="answer_correctness",
        provider="deepeval",
        family="correctness",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=0.8,
        levels=("case", "aggregate"),
        description="Heuristic semantic similarity between actual and expected outputs.",
    ),
    "hallucination": MetricDefinition(
        name="hallucination",
        provider="deepeval",
        family="safety",
        direction=MetricDirection.LOWER_IS_BETTER,
        default_threshold=0.2,
        levels=("case", "aggregate"),
        description="Estimated unsupported content ratio in an answer.",
    ),
    "toxicity": MetricDefinition(
        name="toxicity",
        provider="deepeval",
        family="safety",
        direction=MetricDirection.LOWER_IS_BETTER,
        default_threshold=0.1,
        levels=("case", "aggregate"),
        description="Estimated toxicity score from a simple lexical heuristic.",
    ),
    "faithfulness": MetricDefinition(
        name="faithfulness",
        provider="ragas",
        family="rag",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=0.75,
        levels=("case", "aggregate"),
        description="How well the answer is grounded in retrieved context.",
    ),
    "answer_relevancy": MetricDefinition(
        name="answer_relevancy",
        provider="ragas",
        family="rag",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=0.7,
        levels=("case", "aggregate"),
        description="How relevant the answer is to the question and expected answer.",
    ),
    "context_precision": MetricDefinition(
        name="context_precision",
        provider="ragas",
        family="rag",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=0.7,
        levels=("case", "aggregate"),
        description="Fraction of retrieved context that is useful to answer the query.",
    ),
    "context_recall": MetricDefinition(
        name="context_recall",
        provider="ragas",
        family="rag",
        direction=MetricDirection.HIGHER_IS_BETTER,
        default_threshold=0.7,
        levels=("case", "aggregate"),
        description="Fraction of expected supporting evidence recovered by retrieval.",
    ),
}


def get_metric_definition(name: str) -> MetricDefinition:
    normalized = name.strip().lower()
    if normalized not in _METRICS:
        from core.errors import UnsupportedMetricError

        raise UnsupportedMetricError(
            message=f"Unsupported metric: {name}",
            details={"metric_name": name},
        )
    return _METRICS[normalized]


def list_metric_definitions() -> list[MetricDefinition]:
    return list(_METRICS.values())


def group_metrics_by_provider(metrics: Iterable[str]) -> dict[str, list[MetricDefinition]]:
    grouped: dict[str, list[MetricDefinition]] = {}
    for metric_name in metrics:
        definition = get_metric_definition(metric_name)
        grouped.setdefault(definition.provider, []).append(definition)
    return grouped

