from __future__ import annotations

from datetime import datetime

from pydantic import Field

from domain.schemas import EvalBaseModel, FailureCluster, RunSummary


class ToolEnvelope(EvalBaseModel):
    ok: bool = True
    message: str | None = None
    data: dict = Field(default_factory=dict)


class DashboardOverview(EvalBaseModel):
    project_slug: str
    generated_at: datetime
    recent_runs: list[RunSummary] = Field(default_factory=list)
    failure_clusters: list[FailureCluster] = Field(default_factory=list)
    prompt_inventory: list[dict] = Field(default_factory=list)
    dataset_inventory: list[dict] = Field(default_factory=list)

