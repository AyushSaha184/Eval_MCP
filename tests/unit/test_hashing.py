from __future__ import annotations

from core.hashing import hash_dataset_cases


def test_dataset_hashing_is_deterministic() -> None:
    cases_a = [
        {
            "input_text": "Question",
            "expected_output": "Answer",
            "context": ["A", "B"],
            "labels": ["y", "x"],
            "metadata": {"b": 2, "a": 1},
        }
    ]
    cases_b = [
        {
            "metadata": {"a": 1, "b": 2},
            "labels": ["x", "y"],
            "context": ["A", "B"],
            "expected_output": "Answer",
            "input_text": "Question",
        }
    ]

    assert hash_dataset_cases(cases_a) == hash_dataset_cases(cases_b)

