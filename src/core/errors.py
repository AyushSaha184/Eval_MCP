from __future__ import annotations

from typing import Any


class EvalMCPError(Exception):
    default_code = "eval_mcp_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}

    def __str__(self) -> str:
        return self.message


class ValidationFailed(EvalMCPError):
    default_code = "validation_failed"


class NotFoundError(EvalMCPError):
    default_code = "not_found"


class ConflictError(EvalMCPError):
    default_code = "conflict"


class BackendError(EvalMCPError):
    default_code = "backend_error"


class QueueError(EvalMCPError):
    default_code = "queue_error"


class UnsupportedMetricError(EvalMCPError):
    default_code = "unsupported_metric"


class BaselineResolutionError(EvalMCPError):
    default_code = "baseline_resolution_failed"


class RunExecutionError(EvalMCPError):
    default_code = "run_execution_failed"

