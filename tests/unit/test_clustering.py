from __future__ import annotations

from types import SimpleNamespace

from services.clustering import ClusteringService


def test_failure_clustering_groups_by_failed_metric() -> None:
    bundles = [
        {
            "case_result": SimpleNamespace(id="1", failure_reason="metric_threshold_failed", input_text_snapshot="a"),
            "metrics": [SimpleNamespace(metric_name="answer_correctness", passed=False)],
        },
        {
            "case_result": SimpleNamespace(id="2", failure_reason="metric_threshold_failed", input_text_snapshot="b"),
            "metrics": [SimpleNamespace(metric_name="answer_correctness", passed=False)],
        },
        {
            "case_result": SimpleNamespace(id="3", failure_reason="rag_metric_threshold_failed", input_text_snapshot="c"),
            "metrics": [SimpleNamespace(metric_name="faithfulness", passed=False)],
        },
    ]

    clusters = ClusteringService().cluster_failed_cases(bundles, limit=5)

    assert len(clusters) == 2
    assert clusters[0].cluster_key == "answer_correctness"
    assert clusters[0].size == 2

