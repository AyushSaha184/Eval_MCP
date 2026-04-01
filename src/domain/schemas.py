from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.constants import DEFAULT_CLUSTER_LIMIT, DEFAULT_PAGE_SIZE
from domain.enums import ArtifactType, MetricDirection, RunStatus, RunType, TriggerSource
from domain.types import JSONDict


class EvalBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PaginationParams(EvalBaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=100)


class ProjectCreate(EvalBaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    created_by: str | None = None


class ProjectRead(EvalBaseModel):
    id: str
    slug: str
    name: str
    description: str | None = None
    default_baseline_run_id: str | None = None
    created_by: str | None = None
    created_at: datetime


class PromptReference(EvalBaseModel):
    prompt_id: str | None = None
    prompt_key: str | None = None
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_reference(self) -> "PromptReference":
        if not self.prompt_id and not self.prompt_key:
            raise ValueError("Provide either prompt_id or prompt_key.")
        return self


class PromptRegistration(EvalBaseModel):
    project: str
    prompt_key: str = Field(min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    content: str = Field(min_length=1)
    system_prompt: str | None = None
    metadata: JSONDict = Field(default_factory=dict)
    created_by: str | None = None


class PromptRead(EvalBaseModel):
    id: str
    project_id: str
    prompt_key: str
    version: int
    content: str
    system_prompt: str | None = None
    metadata: JSONDict = Field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime


class AdHocPrompt(EvalBaseModel):
    prompt_key: str | None = None
    content: str = Field(min_length=1)
    system_prompt: str | None = None
    metadata: JSONDict = Field(default_factory=dict)


class DatasetCaseInput(EvalBaseModel):
    input_text: str = Field(min_length=1)
    expected_output: str | None = None
    context: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)


class DatasetReference(EvalBaseModel):
    dataset_id: str | None = None
    dataset_name: str | None = None
    version_hash: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> "DatasetReference":
        if not self.dataset_id and not self.dataset_name:
            raise ValueError("Provide either dataset_id or dataset_name.")
        return self


class DatasetRegistration(EvalBaseModel):
    project: str
    dataset_name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)
    cases: list[DatasetCaseInput] = Field(min_length=1)
    created_by: str | None = None


class DatasetRead(EvalBaseModel):
    id: str
    project_id: str
    dataset_name: str
    version_hash: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)
    case_count: int
    created_by: str | None = None
    created_at: datetime


class DatasetCaseRead(EvalBaseModel):
    id: str
    dataset_id: str
    case_index: int
    input_text: str
    expected_output: str | None = None
    context: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)


class ModelConfig(EvalBaseModel):
    provider: str = "stub"
    model_name: str = "stub-evaluator"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1)
    extra: JSONDict = Field(default_factory=dict)


class RetrieverConfig(EvalBaseModel):
    provider: str
    index_name: str | None = None
    top_k: int = Field(default=4, ge=1)
    extra: JSONDict = Field(default_factory=dict)


class RuntimeConfig(EvalBaseModel):
    max_concurrency: int = Field(default=5, ge=1)
    timeout_seconds: int = Field(default=120, ge=1)
    case_limit: int | None = Field(default=None, ge=1)
    selected_case_indices: list[int] = Field(default_factory=list)
    include_artifacts: bool = False
    labels: list[str] = Field(default_factory=list)
    extra: JSONDict = Field(default_factory=dict)


class RunEvalRequest(EvalBaseModel):
    project: str
    prompt_reference: PromptReference | None = None
    ad_hoc_prompt: AdHocPrompt | None = None
    dataset_reference: DatasetReference
    metrics: list[str] = Field(min_length=1)
    model_settings: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)
    trigger_source: TriggerSource = TriggerSource.MCP
    triggered_by: str | None = None
    baseline_run_id: str | None = None
    force_rerun: bool = False

    @model_validator(mode="after")
    def validate_prompt_source(self) -> "RunEvalRequest":
        if not self.prompt_reference and not self.ad_hoc_prompt:
            raise ValueError("Provide either prompt_reference or ad_hoc_prompt.")
        return self

    @field_validator("metrics")
    @classmethod
    def normalize_metrics(cls, metrics: list[str]) -> list[str]:
        normalized = sorted({metric.strip().lower() for metric in metrics if metric.strip()})
        if not normalized:
            raise ValueError("At least one metric is required.")
        return normalized


class RagCaseInput(EvalBaseModel):
    query: str = Field(min_length=1)
    expected_output: str | None = None
    expected_context: list[str] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)


class RagScoreRequest(EvalBaseModel):
    project: str
    dataset_reference: DatasetReference | None = None
    dataset_name: str | None = None
    cases: list[RagCaseInput] = Field(default_factory=list)
    prompt_reference: PromptReference | None = None
    ad_hoc_prompt: AdHocPrompt | None = None
    retriever_config: RetrieverConfig
    metrics: list[str] = Field(min_length=1)
    model_settings: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)
    trigger_source: TriggerSource = TriggerSource.MCP
    triggered_by: str | None = None
    force_rerun: bool = False

    @model_validator(mode="after")
    def validate_dataset_source(self) -> "RagScoreRequest":
        if not self.dataset_reference and not (self.dataset_name and self.cases):
            raise ValueError(
                "Provide dataset_reference or dataset_name with inline cases."
            )
        if not self.prompt_reference and not self.ad_hoc_prompt:
            raise ValueError("Provide either prompt_reference or ad_hoc_prompt.")
        return self


class RunQueued(EvalBaseModel):
    run_id: str
    status: RunStatus
    cached: bool
    cache_key: str
    source_run_id: str | None = None


class MetricResultView(EvalBaseModel):
    metric_name: str
    metric_family: str
    score: float
    threshold: float | None = None
    direction: MetricDirection
    passed: bool | None = None
    details: JSONDict = Field(default_factory=dict)


class RunSummary(EvalBaseModel):
    run_id: str
    project_slug: str
    run_type: RunType
    status: RunStatus
    prompt_key: str | None = None
    prompt_version: int | None = None
    dataset_name: str | None = None
    dataset_version_hash: str | None = None
    metrics: list[str] = Field(default_factory=list)
    pass_rate: float | None = None
    processed_cases: int = 0
    total_cases: int = 0
    is_cached_result: bool = False
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    labels: list[str] = Field(default_factory=list)


class RunStatusResponse(EvalBaseModel):
    run_id: str
    status: RunStatus
    run_type: RunType
    processed_cases: int = 0
    total_cases: int = 0
    pass_rate: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    is_cached_result: bool = False


class HistoryFilters(PaginationParams):
    project: str
    prompt_key: str | None = None
    dataset_name: str | None = None
    status: RunStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    label: str | None = None


class HistoryResponse(EvalBaseModel):
    items: list[RunSummary]
    total: int
    page: int
    page_size: int


class CompareRequest(EvalBaseModel):
    project: str
    baseline_prompt_reference: PromptReference
    candidate_prompt_reference: PromptReference
    dataset_reference: DatasetReference
    metrics: list[str] = Field(min_length=1)
    model_settings: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)
    trigger_source: TriggerSource = TriggerSource.MCP
    triggered_by: str | None = None
    force_rerun: bool = False


class MetricDelta(EvalBaseModel):
    metric_name: str
    direction: MetricDirection
    baseline_score: float | None = None
    candidate_score: float | None = None
    delta: float | None = None
    improved: bool = False
    regressed: bool = False


class CompareResponse(EvalBaseModel):
    status: str
    baseline_run_id: str
    candidate_run_id: str
    deltas: list[MetricDelta] = Field(default_factory=list)
    improved_metrics: list[str] = Field(default_factory=list)
    regressed_metrics: list[str] = Field(default_factory=list)
    unchanged_metrics: list[str] = Field(default_factory=list)


class RegressionThreshold(EvalBaseModel):
    metric_name: str
    allowed_delta: float = Field(ge=0.0)


class RegressionRequest(EvalBaseModel):
    candidate_run_id: str
    baseline_run_id: str | None = None
    project: str | None = None
    thresholds: list[RegressionThreshold] = Field(default_factory=list)


class RegressionMetricOutcome(EvalBaseModel):
    metric_name: str
    baseline_score: float | None = None
    candidate_score: float | None = None
    delta: float | None = None
    direction: MetricDirection
    allowed_delta: float
    regressed: bool


class RegressionResponse(EvalBaseModel):
    baseline_run_id: str
    candidate_run_id: str
    is_regression: bool
    affected_metrics: list[RegressionMetricOutcome] = Field(default_factory=list)


class FailureCluster(EvalBaseModel):
    cluster_key: str
    title: str
    metric_name: str | None = None
    case_result_ids: list[str] = Field(default_factory=list)
    size: int = 0
    sample_inputs: list[str] = Field(default_factory=list)


class SuggestFixRequest(EvalBaseModel):
    run_id: str
    case_limit: int = Field(default=20, ge=1)
    cluster_limit: int = Field(default=DEFAULT_CLUSTER_LIMIT, ge=1)
    model_name: str | None = None


class SuggestionResponse(EvalBaseModel):
    id: str
    run_id: str
    summary: str
    suggestion_text: str
    failure_clusters: list[FailureCluster] = Field(default_factory=list)
    model_name: str
    created_at: datetime


class BaselineSetRequest(EvalBaseModel):
    project: str
    run_id: str


class AnnotationRequest(EvalBaseModel):
    run_id: str
    label: str = Field(min_length=1, max_length=120)
    note: str | None = None
    created_by: str | None = None


class AnnotationRead(EvalBaseModel):
    id: str
    run_id: str
    label: str
    note: str | None = None
    created_by: str | None = None
    created_at: datetime


class SupportedMetric(EvalBaseModel):
    name: str
    provider: str
    family: str
    direction: MetricDirection
    default_threshold: float | None = None
    levels: list[str] = Field(default_factory=list)
    description: str | None = None


class SupportedMetricsResponse(EvalBaseModel):
    metrics: list[SupportedMetric]
    run_types: list[RunType]
    storage_provider: str
    queue_backend: str


class RerunFailedRequest(EvalBaseModel):
    run_id: str
    triggered_by: str | None = None
    force_rerun: bool = False


class ArtifactReference(EvalBaseModel):
    artifact_type: ArtifactType
    storage_uri: str
    metadata: JSONDict = Field(default_factory=dict)


class NormalizedMetricResult(EvalBaseModel):
    metric_name: str
    metric_family: str
    score: float
    threshold: float | None = None
    direction: MetricDirection
    passed: bool | None = None
    details: JSONDict = Field(default_factory=dict)


class CaseExecutionResult(EvalBaseModel):
    case_index: int
    input_text: str
    expected_output: str | None = None
    actual_output: str | None = None
    retrieved_context: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    token_usage: JSONDict = Field(default_factory=dict)
    status: str
    failure_reason: str | None = None
    metadata: JSONDict = Field(default_factory=dict)
    metrics: list[NormalizedMetricResult] = Field(default_factory=list)


class InternalRunSnapshot(EvalBaseModel):
    prompt_snapshot: JSONDict = Field(default_factory=dict)
    dataset_snapshot: JSONDict = Field(default_factory=dict)
    model_config_snapshot: JSONDict = Field(default_factory=dict)
    retriever_config_snapshot: JSONDict = Field(default_factory=dict)
    runtime_config_snapshot: JSONDict = Field(default_factory=dict)


class RegisterClientRequest(EvalBaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class RegisterClientResponse(EvalBaseModel):
    client_id: str
    identifier: str
    display_name: str | None = None
    project_id: str
    project_slug: str
    onboarding_token: str
    created: bool


class CreateApiKeyRequest(EvalBaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    onboarding_token: str = Field(min_length=1)
    label: str | None = Field(default=None, max_length=120)
    project: str | None = None


class CreateApiKeyResponse(EvalBaseModel):
    key_id: str
    key_prefix: str
    api_key: str
    client_id: str
    identifier: str
    project_id: str
    project_slug: str
    label: str


class CreateScopedApiKeyRequest(EvalBaseModel):
    label: str | None = Field(default=None, max_length=120)
    project: str | None = None


class HostedProjectCreateRequest(EvalBaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class WhoAmIResponse(EvalBaseModel):
    mode: str
    client_id: str | None = None
    identifier: str | None = None
    project_id: str | None = None
    project_slug: str | None = None
    key_id: str | None = None
    key_prefix: str | None = None


class ApiKeyListItem(EvalBaseModel):
    id: str
    label: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
