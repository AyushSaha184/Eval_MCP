from __future__ import annotations

from types import SimpleNamespace

from domain.enums import MetricDirection
from services.comparisons import compute_metric_deltas


def test_comparison_delta_computation_respects_metric_direction() -> None:
    baseline = {
        "answer_correctness": SimpleNamespace(score=0.4, direction=MetricDirection.HIGHER_IS_BETTER),
        "hallucination": SimpleNamespace(score=0.5, direction=MetricDirection.LOWER_IS_BETTER),
    }
    candidate = {
        "answer_correctness": SimpleNamespace(score=0.8, direction=MetricDirection.HIGHER_IS_BETTER),
        "hallucination": SimpleNamespace(score=0.2, direction=MetricDirection.LOWER_IS_BETTER),
    }

    deltas, improved, regressed, unchanged = compute_metric_deltas(baseline, candidate)

    assert len(deltas) == 2
    assert set(improved) == {"answer_correctness", "hallucination"}
    assert regressed == []
    assert unchanged == []

