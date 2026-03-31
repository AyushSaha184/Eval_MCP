from __future__ import annotations

from sqlalchemy import Select, func, select

from db.models import Dataset, EvalRun, MetricResult, Project, Prompt, RunAnnotation, Suggestion


def build_history_statement(project_id: str) -> Select:
    return (
        select(
            EvalRun,
            Project.slug.label("project_slug"),
            Prompt.prompt_key.label("prompt_key"),
            Prompt.version.label("prompt_version"),
            Dataset.dataset_name.label("dataset_name"),
            Dataset.version_hash.label("dataset_version_hash"),
        )
        .join(Project, Project.id == EvalRun.project_id)
        .outerjoin(Prompt, Prompt.id == EvalRun.prompt_ref_id)
        .outerjoin(Dataset, Dataset.id == EvalRun.dataset_ref_id)
        .where(EvalRun.project_id == project_id)
        .order_by(EvalRun.created_at.desc())
    )


def build_aggregate_metric_statement(run_db_id: str) -> Select:
    return (
        select(MetricResult)
        .where(
            MetricResult.run_id == run_db_id,
            MetricResult.case_result_id.is_(None),
        )
        .order_by(MetricResult.metric_name.asc())
    )


def build_metric_trend_statement(project_id: str, metric_name: str) -> Select:
    return (
        select(
            EvalRun.run_id,
            EvalRun.created_at,
            MetricResult.score,
        )
        .join(MetricResult, MetricResult.run_id == EvalRun.id)
        .where(
            EvalRun.project_id == project_id,
            MetricResult.metric_name == metric_name,
            MetricResult.case_result_id.is_(None),
        )
        .order_by(EvalRun.created_at.asc())
    )


def build_recent_suggestions_statement(project_id: str) -> Select:
    return (
        select(Suggestion, EvalRun.run_id)
        .join(EvalRun, EvalRun.id == Suggestion.run_id)
        .where(EvalRun.project_id == project_id)
        .order_by(Suggestion.created_at.desc())
    )


def build_label_counts_statement(project_id: str) -> Select:
    return (
        select(RunAnnotation.label, func.count(RunAnnotation.id))
        .join(EvalRun, EvalRun.id == RunAnnotation.run_id)
        .where(EvalRun.project_id == project_id)
        .group_by(RunAnnotation.label)
        .order_by(func.count(RunAnnotation.id).desc(), RunAnnotation.label.asc())
    )

