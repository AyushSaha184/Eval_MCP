from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from domain.enums import ArtifactType, CaseResultStatus, MetricDirection, RunStatus, RunType, TriggerSource


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    owner_client_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_baseline_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    owner_client: Mapped["Client | None"] = relationship(back_populates="projects")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    eval_runs: Mapped[list["EvalRun"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="EvalRun.project_id",
    )


class Client(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clients"

    account_identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onboarding_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    projects: Mapped[list[Project]] = relationship(back_populates="owner_client")
    api_keys: Mapped[list["ClientApiKey"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )


class ClientApiKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "client_api_keys"
    __table_args__ = (
        Index("ix_client_api_keys_client_project_active", "client_id", "project_id", "is_active"),
    )

    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship(back_populates="api_keys")
    project: Mapped[Project] = relationship()


class Prompt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("project_id", "prompt_key", "version", name="uq_prompts_project_key_version"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    project: Mapped[Project] = relationship(back_populates="prompts")
    eval_runs: Mapped[list["EvalRun"]] = relationship(back_populates="prompt_ref")


class Dataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "dataset_name",
            "version_hash",
            name="uq_datasets_project_name_versionhash",
        ),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    project: Mapped[Project] = relationship(back_populates="datasets")
    cases: Mapped[list["DatasetCase"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetCase.case_index",
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(back_populates="dataset_ref")


class DatasetCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dataset_cases"
    __table_args__ = (
        UniqueConstraint("dataset_id", "case_index", name="uq_dataset_cases_dataset_case_index"),
    )

    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_index: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    labels_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    dataset: Mapped[Dataset] = relationship(back_populates="cases")
    eval_case_results: Mapped[list["EvalCaseResult"]] = relationship(back_populates="dataset_case")


class EvalRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "eval_runs"
    __table_args__ = (
        Index("ix_eval_runs_project_status_created", "project_id", "status", "created_at"),
    )

    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_type: Mapped[RunType] = mapped_column(
        Enum(RunType, native_enum=False),
        nullable=False,
        default=RunType.PROMPT_EVAL,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False),
        nullable=False,
        default=RunStatus.QUEUED,
        index=True,
    )
    trigger_source: Mapped[TriggerSource] = mapped_column(
        Enum(TriggerSource, native_enum=False),
        nullable=False,
        default=TriggerSource.MCP,
    )
    triggered_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_ref_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_ref_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    baseline_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    metrics_requested_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_cached_result: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="eval_runs", foreign_keys=[project_id])
    prompt_ref: Mapped[Prompt | None] = relationship(back_populates="eval_runs")
    dataset_ref: Mapped[Dataset | None] = relationship(back_populates="eval_runs")
    baseline_run: Mapped["EvalRun | None"] = relationship(remote_side="EvalRun.id")
    snapshot: Mapped["RunSnapshot | None"] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        uselist=False,
    )
    case_results: Mapped[list["EvalCaseResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvalCaseResult.case_index",
    )
    metric_results: Mapped[list["MetricResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    annotations: Mapped[list["RunAnnotation"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class RunSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "run_snapshots"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    prompt_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    dataset_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    model_config_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    retriever_config_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    runtime_config_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[EvalRun] = relationship(back_populates="snapshot")


class EvalCaseResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "eval_case_results"
    __table_args__ = (
        UniqueConstraint("run_id", "case_index", name="uq_eval_case_results_run_case_index"),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_case_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("dataset_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    case_index: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_context_snapshot_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_usage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[CaseResultStatus] = mapped_column(
        Enum(CaseResultStatus, native_enum=False),
        nullable=False,
        default=CaseResultStatus.PASSED,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[EvalRun] = relationship(back_populates="case_results")
    dataset_case: Mapped[DatasetCase | None] = relationship(back_populates="eval_case_results")
    metric_results: Mapped[list["MetricResult"]] = relationship(
        back_populates="case_result",
        cascade="all, delete-orphan",
    )


class MetricResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "metric_results"
    __table_args__ = (
        Index("ix_metric_results_run_metric_case", "run_id", "metric_name", "case_result_id"),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_result_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("eval_case_results.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    metric_family: Mapped[str] = mapped_column(String(120), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction: Mapped[MetricDirection] = mapped_column(
        Enum(MetricDirection, native_enum=False),
        nullable=False,
    )
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[EvalRun] = relationship(back_populates="metric_results")
    case_result: Mapped[EvalCaseResult | None] = relationship(back_populates="metric_results")


class Suggestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "suggestions"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    failure_clusters_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[EvalRun] = relationship(back_populates="suggestions")


class Artifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "artifacts"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, native_enum=False),
        nullable=False,
    )
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped[EvalRun] = relationship(back_populates="artifacts")


class RunAnnotation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "run_annotations"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    run: Mapped[EvalRun] = relationship(back_populates="annotations")


class ScheduledJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scheduled_jobs"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(120), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    cron_expr: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
