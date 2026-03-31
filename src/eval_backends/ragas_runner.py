from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from core.config import get_settings
from core.metrics_registry import get_metric_definition
from domain.enums import MetricDirection
from domain.schemas import NormalizedMetricResult


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _token_set(values: str | list[str] | None) -> set[str]:
    if isinstance(values, list):
        return set(" ".join(values).lower().split())
    return set(_normalize_text(values).split())


class RagasRunner:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def score_case(
        self,
        *,
        metrics: Iterable[str],
        question: str,
        actual_output: str | None,
        expected_output: str | None,
        retrieved_context: list[str] | None,
        expected_context: list[str] | None = None,
    ) -> list[NormalizedMetricResult]:
        answer = _normalize_text(actual_output)
        expected = _normalize_text(expected_output)
        context_tokens = _token_set(retrieved_context)
        expected_context_tokens = _token_set(expected_context)
        question_tokens = _token_set(question)
        results: list[NormalizedMetricResult] = []

        if self.settings.use_live_ragas:
            live_results = await self._score_case_live(
                metrics=metrics,
                question=question,
                actual_output=actual_output,
                expected_output=expected_output,
                retrieved_context=retrieved_context,
                expected_context=expected_context,
            )
            if live_results:
                return live_results

        for metric_name in metrics:
            definition = get_metric_definition(metric_name)
            if definition.provider != "ragas":
                continue

            if metric_name == "faithfulness":
                answer_tokens = _token_set(answer)
                overlap = len(answer_tokens & context_tokens) / max(len(answer_tokens), 1) if answer_tokens else 0.0
                score = overlap
            elif metric_name == "answer_relevancy":
                score = SequenceMatcher(None, f"{question} {answer}", f"{question} {expected}").ratio()
            elif metric_name == "context_precision":
                score = len(context_tokens & expected_context_tokens) / max(len(context_tokens), 1) if context_tokens else 0.0
            elif metric_name == "context_recall":
                score = len(context_tokens & expected_context_tokens) / max(len(expected_context_tokens), 1) if expected_context_tokens else 0.0
            else:
                continue

            passed = None
            if definition.default_threshold is not None:
                if definition.direction == MetricDirection.HIGHER_IS_BETTER:
                    passed = score >= definition.default_threshold
                else:
                    passed = score <= definition.default_threshold
            results.append(
                NormalizedMetricResult(
                    metric_name=definition.name,
                    metric_family=definition.family,
                    score=round(score, 6),
                    threshold=definition.default_threshold,
                    direction=definition.direction,
                    passed=passed,
                    details={"provider": definition.provider, "question_terms": len(question_tokens)},
                )
            )
        return results

    async def _score_case_live(
        self,
        *,
        metrics: Iterable[str],
        question: str,
        actual_output: str | None,
        expected_output: str | None,
        retrieved_context: list[str] | None,
        expected_context: list[str] | None = None,
    ) -> list[NormalizedMetricResult]:
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        except ImportError:
            return []

        metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }
        selected = [metric_map[name] for name in metrics if name in metric_map]
        if not selected:
            return []
        dataset = Dataset.from_dict(
            {
                "question": [question],
                "answer": [actual_output or ""],
                "ground_truth": [expected_output or ""],
                "contexts": [retrieved_context or []],
                "reference_contexts": [expected_context or []],
            }
        )
        scores = evaluate(dataset, metrics=selected)
        results: list[NormalizedMetricResult] = []
        for metric_name in metrics:
            if metric_name not in metric_map:
                continue
            definition = get_metric_definition(metric_name)
            raw_score = float(scores[metric_name][0])
            passed = (
                raw_score >= definition.default_threshold
                if definition.default_threshold is not None and definition.direction == MetricDirection.HIGHER_IS_BETTER
                else raw_score <= definition.default_threshold
                if definition.default_threshold is not None
                else None
            )
            results.append(
                NormalizedMetricResult(
                    metric_name=definition.name,
                    metric_family=definition.family,
                    score=round(raw_score, 6),
                    threshold=definition.default_threshold,
                    direction=definition.direction,
                    passed=passed,
                    details={"provider": "ragas", "mode": "live"},
                )
            )
        return results
