from __future__ import annotations

import pytest

from eval_backends.deepeval_runner import DeepEvalRunner


@pytest.mark.asyncio
async def test_metric_backend_returns_normalized_metric_names() -> None:
    results = await DeepEvalRunner().score_case(
        metrics=["answer_correctness", "exact_match"],
        actual_output="Paris",
        expected_output="Paris",
        context=["France has capital Paris"],
    )

    assert {result.metric_name for result in results} == {"answer_correctness", "exact_match"}

