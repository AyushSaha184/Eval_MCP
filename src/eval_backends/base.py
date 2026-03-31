from __future__ import annotations

from pydantic import Field

from domain.schemas import EvalBaseModel, FailureCluster, NormalizedMetricResult
from domain.types import JSONDict


class GenerationResult(EvalBaseModel):
    output_text: str
    rendered_prompt: str
    latency_ms: int = 0
    token_usage: JSONDict = Field(default_factory=dict)
    retrieved_context: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)


class BackendMetricBatch(EvalBaseModel):
    metrics: list[NormalizedMetricResult] = Field(default_factory=list)


class JudgeSuggestionResult(EvalBaseModel):
    summary: str
    suggestion_text: str
    failure_clusters: list[FailureCluster] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)

