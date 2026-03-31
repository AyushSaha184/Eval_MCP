from __future__ import annotations

from services.caching import CachingService


def test_cache_key_generation_is_deterministic_and_metric_order_independent() -> None:
    service = CachingService(session=None)  # type: ignore[arg-type]
    base_kwargs = {
        "project_id": "project-1",
        "run_type": "prompt_eval",
        "prompt_snapshot": {"content": "good prompt"},
        "dataset_snapshot": {"version_hash": "abc123", "selected_case_indices": []},
        "model_config": {"provider": "stub", "model_name": "stub"},
        "retriever_config": None,
        "runtime_config": {"max_concurrency": 2},
    }
    key_a = service.build_run_cache_key(metrics=["exact_match", "answer_correctness"], **base_kwargs)
    key_b = service.build_run_cache_key(metrics=["answer_correctness", "exact_match"], **base_kwargs)
    key_c = service.build_run_cache_key(metrics=["exact_match"], **base_kwargs)

    assert key_a == key_b
    assert key_a != key_c

