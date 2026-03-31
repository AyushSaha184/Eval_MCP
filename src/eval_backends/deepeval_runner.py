from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from core.config import get_settings
from core.metrics_registry import get_metric_definition
from domain.enums import MetricDirection
from domain.schemas import NormalizedMetricResult


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _token_set(value: str | None) -> set[str]:
    return set(_normalize_text(value).split())


class DeepEvalRunner:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def score_case(
        self,
        *,
        metrics: Iterable[str],
        actual_output: str | None,
        expected_output: str | None,
        context: list[str] | None = None,
    ) -> list[NormalizedMetricResult]:
        actual = _normalize_text(actual_output)
        expected = _normalize_text(expected_output)
        joined_context = " ".join(context or [])
        context_tokens = _token_set(joined_context) | _token_set(expected_output)
        scores: list[NormalizedMetricResult] = []

        if self.settings.use_live_deepeval:
            live_results = await self._score_case_live(
                metrics=metrics,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context,
            )
            if live_results:
                return live_results

        for metric_name in metrics:
            definition = get_metric_definition(metric_name)
            if definition.provider not in {"deepeval", "internal"}:
                continue
            if metric_name == "exact_match":
                score = 1.0 if actual == expected and expected else 0.0
            elif metric_name == "answer_correctness":
                score = SequenceMatcher(None, actual, expected).ratio() if expected else 0.0
            elif metric_name == "hallucination":
                actual_tokens = _token_set(actual_output)
                unsupported = [token for token in actual_tokens if token not in context_tokens]
                score = (len(unsupported) / max(len(actual_tokens), 1)) if actual_tokens else 0.0
            elif metric_name == "toxicity":
                toxic_terms = {"hate", "idiot", "stupid", "kill", "racist"}
                score = 1.0 if toxic_terms & _token_set(actual_output) else 0.0
            else:
                continue

            passed = None
            if definition.default_threshold is not None:
                if definition.direction == MetricDirection.HIGHER_IS_BETTER:
                    passed = score >= definition.default_threshold
                else:
                    passed = score <= definition.default_threshold
            scores.append(
                NormalizedMetricResult(
                    metric_name=definition.name,
                    metric_family=definition.family,
                    score=round(score, 6),
                    threshold=definition.default_threshold,
                    direction=definition.direction,
                    passed=passed,
                    details={"provider": definition.provider},
                )
            )
        return scores

    async def _score_case_live(
        self,
        *,
        metrics: Iterable[str],
        actual_output: str | None,
        expected_output: str | None,
        context: list[str] | None = None,
    ) -> list[NormalizedMetricResult]:
        try:
            from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric, ToxicityMetric
            from deepeval.test_case import LLMTestCase
        except ImportError:
            return []

        metric_map = {
            "answer_correctness": AnswerRelevancyMetric(threshold=get_metric_definition("answer_correctness").default_threshold or 0.8),
            "hallucination": HallucinationMetric(threshold=get_metric_definition("hallucination").default_threshold or 0.2),
            "toxicity": ToxicityMetric(threshold=get_metric_definition("toxicity").default_threshold or 0.1),
        }
        test_case = LLMTestCase(
            input="",
            actual_output=actual_output or "",
            expected_output=expected_output or "",
            context=context or [],
        )
        results: list[NormalizedMetricResult] = []
        for metric_name in metrics:
            definition = get_metric_definition(metric_name)
            if metric_name == "exact_match":
                continue
            metric = metric_map.get(metric_name)
            if metric is None:
                continue
            metric.measure(test_case)
            score = float(getattr(metric, "score", 0.0) or 0.0)
            results.append(
                NormalizedMetricResult(
                    metric_name=definition.name,
                    metric_family=definition.family,
                    score=round(score, 6),
                    threshold=definition.default_threshold,
                    direction=definition.direction,
                    passed=bool(getattr(metric, "success", None)) if hasattr(metric, "success") else None,
                    details={"provider": "deepeval", "mode": "live"},
                )
            )
        return results
