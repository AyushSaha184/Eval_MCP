from __future__ import annotations

from domain.enums import MetricDirection
from services.regressions import is_metric_regression


def test_regression_threshold_logic_handles_direction() -> None:
    assert is_metric_regression(
        direction=MetricDirection.HIGHER_IS_BETTER,
        baseline_score=0.9,
        candidate_score=0.7,
        allowed_delta=0.05,
    )
    assert not is_metric_regression(
        direction=MetricDirection.LOWER_IS_BETTER,
        baseline_score=0.2,
        candidate_score=0.22,
        allowed_delta=0.05,
    )

