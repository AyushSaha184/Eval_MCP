from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunType(StrEnum):
    PROMPT_EVAL = "prompt_eval"
    RAG_EVAL = "rag_eval"
    COMPARISON_BACKING_RUN = "comparison_backing_run"
    SUGGESTION_EVAL = "suggestion_eval"


class TriggerSource(StrEnum):
    MCP = "mcp"
    API = "api"
    CLI = "cli"
    SCHEDULE = "schedule"
    CI = "ci"


class MetricDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class ArtifactType(StrEnum):
    TRANSCRIPT = "transcript"
    RETRIEVED_CONTEXT = "retrieved_context"
    PROMPTFOO_REPORT = "promptfoo_report"
    COMPARISON_REPORT = "comparison_report"
    DEBUG_BUNDLE = "debug_bundle"


class CaseResultStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

