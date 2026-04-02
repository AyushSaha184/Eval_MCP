from __future__ import annotations

from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from core.logging import setup_logging
from db.models import EvalCaseResult, EvalRun, MetricResult
from db.queries import build_metric_trend_statement, build_recent_suggestions_statement
from db.session import session_scope
from domain.enums import RunStatus
from domain.schemas import HistoryFilters
from services.comparisons import compute_metric_deltas
from services.datasets import DatasetService
from services.history import HistoryService
from services.projects import ProjectService
from services.prompts import PromptService


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    head_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def _render_layout(*, project_options: list[str], selected_project: str, sections: list[tuple[str, str]]) -> str:
    options = "".join(
        f"<option value='{escape(project)}' {'selected' if project == selected_project else ''}>{escape(project)}</option>"
        for project in project_options
    )
    section_html = "".join(
        f"<section class='card'><h2>{escape(title)}</h2>{content}</section>" for title, content in sections
    )
    return f"""
    <html>
      <head>
        <title>Eval_MCP Dashboard</title>
        <style>
          body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: linear-gradient(180deg, #f7f3ea, #f2f7fb); color: #102a43; }}
          header {{ padding: 24px 32px; background: #143642; color: white; }}
          main {{ padding: 24px 32px; display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; }}
          .card {{ background: white; border-radius: 16px; padding: 18px; box-shadow: 0 12px 30px rgba(16, 42, 67, 0.08); }}
          h1, h2 {{ margin-top: 0; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e8eef2; vertical-align: top; }}
          th {{ color: #486581; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
          .muted {{ color: #627d98; }}
          .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #f0f4f8; margin-right: 6px; margin-bottom: 6px; }}
          form {{ display: flex; gap: 12px; align-items: center; margin-top: 12px; }}
          select, button {{ padding: 8px 12px; border-radius: 10px; border: 1px solid #bcccdc; }}
          button {{ background: #d1495b; color: white; border: none; }}
        </style>
      </head>
      <body>
        <header>
          <h1>Eval_MCP Dashboard</h1>
          <div class="muted">Read-only internal view for projects, runs, trends, failures, and suggestions.</div>
          <form method="get">
            <label for="project">Project</label>
            <select id="project" name="project">{options}</select>
            <button type="submit">Load</button>
          </form>
        </header>
        <main>{section_html}</main>
      </body>
    </html>
    """


app = FastAPI(title="Eval_MCP Dashboard", version="0.1.0")
setup_logging()


@app.get("/", response_class=HTMLResponse)
async def dashboard(project: str | None = None) -> HTMLResponse:
    async with session_scope() as session:
        project_service = ProjectService(session)
        projects = await project_service.list_projects()
        if not projects:
            return HTMLResponse("<h1>Eval_MCP Dashboard</h1><p>No projects found yet.</p>")

        selected_project = project or projects[0].slug
        project_model = await project_service.get_project_model(selected_project)

        history = await HistoryService(session).get_eval_history(
            HistoryFilters(project=project_model.id, page=1, page_size=10)
        )
        datasets = await DatasetService(session).list_datasets(project_model.id)
        prompts = await PromptService(session).list_prompts(project_model.id)

        status_rows = (
            await session.execute(
                select(EvalRun.status, func.count(EvalRun.id))
                .where(EvalRun.project_id == project_model.id)
                .group_by(EvalRun.status)
                .order_by(EvalRun.status.asc())
            )
        ).all()
        status_table = _render_table(
            ["Status", "Count"],
            [[str(status), str(count)] for status, count in status_rows],
        )

        recent_runs_table = _render_table(
            ["Run", "Type", "Status", "Pass Rate", "Cases"],
            [
                [
                    escape(item.run_id),
                    escape(str(item.run_type)),
                    escape(str(item.status)),
                    escape(f"{(item.pass_rate or 0.0):.2%}"),
                    escape(f"{item.processed_cases}/{item.total_cases}"),
                ]
                for item in history.items
            ],
        )

        metric_rows = []
        for metric_name in ("answer_correctness", "exact_match", "faithfulness", "context_precision"):
            points = (
                await session.execute(build_metric_trend_statement(project_model.id, metric_name))
            ).all()
            if not points:
                continue
            metric_rows.append(
                [
                    escape(metric_name),
                    escape(str(len(points))),
                    escape(", ".join(f"{row.score:.2f}" for row in points[-5:])),
                ]
            )
        metric_trends_table = _render_table(
            ["Metric", "Points", "Latest Scores"],
            metric_rows or [["No metric trend data yet.", "", ""]],
        )

        baseline_section = "<p class='muted'>No project baseline configured.</p>"
        if project_model.default_baseline_run_id:
            baseline_run = await session.get(EvalRun, project_model.default_baseline_run_id)
            latest_completed = (
                await session.execute(
                    select(EvalRun)
                    .where(
                        EvalRun.project_id == project_model.id,
                        EvalRun.status == RunStatus.COMPLETED,
                        EvalRun.id != project_model.default_baseline_run_id,
                    )
                    .order_by(EvalRun.completed_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if baseline_run and latest_completed:
                baseline_metrics = {
                    metric.metric_name: metric
                    for metric in (
                        await session.execute(
                            select(MetricResult).where(
                                MetricResult.run_id == baseline_run.id,
                                MetricResult.case_result_id.is_(None),
                            )
                        )
                    ).scalars()
                }
                candidate_metrics = {
                    metric.metric_name: metric
                    for metric in (
                        await session.execute(
                            select(MetricResult).where(
                                MetricResult.run_id == latest_completed.id,
                                MetricResult.case_result_id.is_(None),
                            )
                        )
                    ).scalars()
                }
                deltas, improved, regressed, unchanged = compute_metric_deltas(
                    baseline_metrics,
                    candidate_metrics,
                )
                baseline_section = (
                    f"<p><strong>Baseline:</strong> {escape(baseline_run.run_id)}<br>"
                    f"<strong>Candidate:</strong> {escape(latest_completed.run_id)}</p>"
                    + _render_table(
                        ["Metric", "Baseline", "Candidate", "Delta"],
                        [
                            [
                                escape(item.metric_name),
                                escape(f"{item.baseline_score or 0:.3f}"),
                                escape(f"{item.candidate_score or 0:.3f}"),
                                escape(f"{item.delta or 0:.3f}"),
                            ]
                            for item in deltas
                        ],
                    )
                    + f"<p><span class='pill'>Improved: {', '.join(improved) or 'None'}</span>"
                    + f"<span class='pill'>Regressed: {', '.join(regressed) or 'None'}</span>"
                    + f"<span class='pill'>Unchanged: {', '.join(unchanged) or 'None'}</span></p>"
                )

        failure_rows = (
            await session.execute(
                select(EvalCaseResult, EvalRun.run_id)
                .join(EvalRun, EvalRun.id == EvalCaseResult.run_id)
                .where(
                    EvalRun.project_id == project_model.id,
                    EvalCaseResult.status.in_(("failed", "error")),
                )
                .order_by(EvalCaseResult.created_at.desc())
                .limit(10)
            )
        ).all()
        failure_table = _render_table(
            ["Run", "Case", "Input", "Reason"],
            [
                [
                    escape(run_id),
                    escape(str(case.case_index)),
                    escape(case.input_text_snapshot[:80]),
                    escape(case.failure_reason or "n/a"),
                ]
                for case, run_id in failure_rows
            ]
            or [["No failing cases recorded.", "", "", ""]],
        )

        suggestion_rows = (await session.execute(build_recent_suggestions_statement(project_model.id))).all()
        suggestions_table = _render_table(
            ["Run", "Summary", "Model"],
            [
                [
                    escape(run_id),
                    escape(suggestion.summary[:120]),
                    escape(suggestion.model_name),
                ]
                for suggestion, run_id in suggestion_rows[:10]
            ]
            or [["No suggestions generated yet.", "", ""]],
        )
        latest_clusters = suggestion_rows[0][0].failure_clusters_json if suggestion_rows else []
        failure_clusters_html = "".join(
            f"<span class='pill'>{escape(cluster['title'])} ({cluster['size']})</span>" for cluster in latest_clusters
        ) or "<p class='muted'>No failure clusters available yet.</p>"

        dataset_table = _render_table(
            ["Dataset", "Version", "Cases"],
            [
                [
                    escape(dataset.dataset_name),
                    escape(dataset.version_hash[:12]),
                    escape(str(dataset.case_count)),
                ]
                for dataset in datasets
            ],
        )
        prompt_table = _render_table(
            ["Prompt", "Version", "Created"],
            [
                [
                    escape(prompt.prompt_key),
                    escape(str(prompt.version)),
                    escape(prompt.created_at.isoformat()),
                ]
                for prompt in prompts
            ],
        )

        overview = (
            f"<p><strong>Project:</strong> {escape(project_model.slug)}</p>"
            f"<p><strong>Prompts:</strong> {len(prompts)}<br>"
            f"<strong>Datasets:</strong> {len(datasets)}<br>"
            f"<strong>Runs:</strong> {history.total}</p>"
            + status_table
        )

        html = _render_layout(
            project_options=[project.slug for project in projects],
            selected_project=project_model.slug,
            sections=[
                ("Project Overview", overview),
                ("Recent Runs", recent_runs_table),
                ("Pass-Rate And Metric Trends", metric_trends_table),
                ("Baseline vs Candidate", baseline_section),
                ("Failure Explorer", failure_table),
                ("Failure Clusters", failure_clusters_html),
                ("Suggestions History", suggestions_table),
                ("Dataset Inventory", dataset_table),
                ("Prompt Inventory", prompt_table),
            ],
        )
        return HTMLResponse(html)

