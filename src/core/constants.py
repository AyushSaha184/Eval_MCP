from __future__ import annotations

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_PROMPT_METRICS = ("answer_correctness", "exact_match")
DEFAULT_RAG_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)
DEFAULT_CLUSTER_LIMIT = 5
AGGREGATE_METRIC_SENTINEL = "__aggregate__"
NON_CACHE_RUNTIME_FIELDS = {
    "force_rerun",
    "requested_by",
    "labels",
    "notes",
    "description",
}

