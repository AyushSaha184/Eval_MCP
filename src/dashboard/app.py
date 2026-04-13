from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from prefab_ui import PrefabApp
from prefab_ui.components import (
    Badge,
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    DataTable,
    DataTableColumn,
    Div,
    H1,
    Link,
    Metric,
    Muted,
    P,
    Text,
)
from prefab_ui.themes import Theme
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


def _normalize_column_key(header: str, index: int) -> str:
    base = "".join(char.lower() if char.isalnum() else "_" for char in header).strip("_")
    return base or f"column_{index}"


def _build_table(headers: list[str], rows: list[list[object]], *, page_size: int = 10, search: bool = False) -> DataTable:
    column_keys = [_normalize_column_key(header, index) for index, header in enumerate(headers)]
    return DataTable(
        columns=[
            DataTableColumn(key=key, header=header, sortable=index == 0)
            for index, (key, header) in enumerate(zip(column_keys, headers, strict=True))
        ],
        rows=[
            {
                key: str(row[index]) if row[index] is not None else ""
                for index, key in enumerate(column_keys)
            }
            for row in rows
        ],
        paginated=len(rows) > page_size,
        page_size=page_size,
        search=search,
    )


def _build_card(title: str, body: object, *, description: str | None = None) -> Card:
    header_children: list[object] = [CardTitle(title)]
    if description:
        header_children.append(CardDescription(description))
    return Card(
        css_class="border-white/60 bg-white/78 shadow-[0_24px_80px_rgba(10,37,64,0.08)] backdrop-blur",
        children=[
            CardHeader(children=header_children),
            CardContent(children=[body] if not isinstance(body, list) else body),
        ]
    )


def _build_badge_row(items: list[str], *, empty_message: str) -> Div:
    if not items:
        return Div(children=[Muted(empty_message)])
    return Div(
        css_class="flex flex-wrap gap-2",
        children=[Badge(item, variant="secondary") for item in items],
    )


def _build_project_links(project_options: list[str], selected_project: str) -> Div:
    return Div(
        css_class="flex flex-wrap gap-3",
        children=[
            Link(
                project,
                href=f"/?project={quote(project)}",
                target="_self",
                css_class=(
                    "inline-flex items-center rounded-full border px-3 py-1 text-sm "
                    + (
                        "bg-primary text-primary-foreground border-primary"
                        if project == selected_project
                        else "bg-background text-foreground border-border hover:bg-muted"
                    )
                ),
            )
            for project in project_options
        ],
    )


def _dashboard_theme() -> Theme:
    return Theme(
        light_css=(
            "--background: #08131a;"
            " --foreground: #edf7f8;"
            " --card: rgba(11,26,33,0.82);"
            " --card-foreground: #edf7f8;"
            " --popover: rgba(10,20,27,0.96);"
            " --popover-foreground: #edf7f8;"
            " --primary: #34d399;"
            " --primary-foreground: #06231c;"
            " --secondary: #0f2a33;"
            " --secondary-foreground: #d4f7ef;"
            " --muted: #0e2028;"
            " --muted-foreground: #8fa8b1;"
            " --accent: #10333a;"
            " --accent-foreground: #d4f7ef;"
            " --border: rgba(120, 221, 195, 0.14);"
            " --input: rgba(15,34,42,0.92);"
            " --ring: #34d399;"
            " --radius: 1.2rem;"
        ),
        css="""
body {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(52, 211, 153, 0.16), transparent 28%),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 24%),
    linear-gradient(180deg, #040b10 0%, #07131a 46%, #09171d 100%);
}

.pf-app-root {
  position: relative;
}

.pf-app-root::before {
  content: "";
  position: absolute;
  inset: 0 auto auto 0;
  width: 18rem;
  height: 18rem;
  border-radius: 999px;
  background: rgba(52, 211, 153, 0.08);
  filter: blur(40px);
  z-index: -1;
}

a {
  transition: all 160ms ease;
}
""",
        font="Space Grotesk",
        font_mono="IBM Plex Mono",
        mode="dark",
        gradient=False,
    )


app = FastAPI(title="Eval_MCP Dashboard", version="0.1.0")
setup_logging()


@app.get("/", response_class=HTMLResponse)
async def dashboard(project: str | None = None) -> HTMLResponse:
    async with session_scope() as session:
        project_service = ProjectService(session)
        projects = await project_service.list_projects()
        if not projects:
            empty_app = PrefabApp(
                title="Eval_MCP Dashboard",
                theme=_dashboard_theme(),
                css_class="min-h-screen px-6 py-10 md:px-10",
                view=Div(
                    css_class="mx-auto max-w-6xl space-y-8",
                    children=[
                        Div(
                            css_class="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]",
                            children=[
                                Div(
                                    css_class="space-y-5 rounded-[2rem] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.88),rgba(227,247,242,0.78))] p-8 shadow-[0_30px_120px_rgba(15,118,110,0.12)] backdrop-blur",
                                    children=[
                                        Badge("Prefab UI active", variant="secondary"),
                                        H1("Eval_MCP Dashboard"),
                                        P("The dashboard renderer is live. What you are seeing is the empty-state because this database has no projects yet."),
                                        Muted("Create or seed a project, prompt, dataset, and run to light up the rest of the dashboard."),
                                        Div(
                                            css_class="flex flex-wrap gap-2 pt-2",
                                            children=[
                                                Badge("FastAPI", variant="outline"),
                                                Badge("Prefab", variant="outline"),
                                                Badge("Postgres", variant="outline"),
                                                Badge("Read-only view", variant="outline"),
                                            ],
                                        ),
                                    ],
                                ),
                                _build_card(
                                    "Next Step",
                                    [
                                        Text("No projects found yet."),
                                        Muted("Once data exists, this page will expand into the full run, trend, failure, suggestion, dataset, and prompt panels."),
                                    ],
                                    description="Empty-state summary",
                                ),
                            ],
                        ),
                    ],
                ),
            )
            return HTMLResponse(empty_app.html(renderer_mode="bundled"))

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

        recent_run_rows = [
            [
                item.run_id,
                str(item.run_type),
                str(item.status),
                f"{(item.pass_rate or 0.0):.2%}",
                f"{item.processed_cases}/{item.total_cases}",
            ]
            for item in history.items
        ]

        metric_rows: list[list[object]] = []
        for metric_name in ("answer_correctness", "exact_match", "faithfulness", "context_precision"):
            points = (await session.execute(build_metric_trend_statement(project_model.id, metric_name))).all()
            if not points:
                continue
            metric_rows.append([metric_name, len(points), ", ".join(f"{row.score:.2f}" for row in points[-5:])])

        baseline_components: list[object] = [Muted("No project baseline configured.")]
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
                baseline_components = [
                    Text(f"Baseline: {baseline_run.run_id}"),
                    Text(f"Candidate: {latest_completed.run_id}"),
                    _build_badge_row(
                        [f"Improved: {', '.join(improved) or 'None'}", f"Regressed: {', '.join(regressed) or 'None'}", f"Unchanged: {', '.join(unchanged) or 'None'}"],
                        empty_message="No baseline delta summary available.",
                    ),
                    _build_table(
                        ["Metric", "Baseline", "Candidate", "Delta"],
                        [
                            [
                                item.metric_name,
                                f"{item.baseline_score or 0:.3f}",
                                f"{item.candidate_score or 0:.3f}",
                                f"{item.delta or 0:.3f}",
                            ]
                            for item in deltas
                        ],
                        page_size=10,
                    ),
                ]

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

        suggestion_rows = (await session.execute(build_recent_suggestions_statement(project_model.id))).all()
        latest_clusters = suggestion_rows[0][0].failure_clusters_json if suggestion_rows else []

        summary_metrics = Div(
            css_class="grid gap-4 md:grid-cols-2 xl:grid-cols-4",
            children=[
                Metric(label="Project", value=project_model.slug, description="Active dashboard scope"),
                Metric(label="Prompts", value=len(prompts), description="Prompt versions tracked"),
                Metric(label="Datasets", value=len(datasets), description="Dataset versions available"),
                Metric(label="Runs", value=history.total, description="Historical evaluation runs"),
            ],
        )

        content = Div(
            css_class="mx-auto max-w-7xl space-y-8",
            children=[
                Div(
                    css_class="space-y-4",
                    children=[
                        H1("Eval_MCP Dashboard"),
                        Muted("Prefab-rendered operator view for projects, runs, trends, failures, and suggestions."),
                        _build_project_links([project.slug for project in projects], project_model.slug),
                    ],
                ),
                summary_metrics,
                Div(
                    css_class="grid gap-6 xl:grid-cols-2",
                    children=[
                        _build_card(
                            "Project Overview",
                            _build_table(
                                ["Status", "Count"],
                                [[str(status), count] for status, count in status_rows],
                                page_size=10,
                            ),
                            description=f"Selected project: {project_model.slug}",
                        ),
                        _build_card(
                            "Recent Runs",
                            _build_table(
                                ["Run", "Type", "Status", "Pass Rate", "Cases"],
                                recent_run_rows or [["No runs recorded yet.", "", "", "", ""]],
                                search=True,
                            ),
                        ),
                        _build_card(
                            "Pass-Rate And Metric Trends",
                            _build_table(
                                ["Metric", "Points", "Latest Scores"],
                                metric_rows or [["No metric trend data yet.", "", ""]],
                            ),
                        ),
                        _build_card("Baseline vs Candidate", baseline_components),
                        _build_card(
                            "Failure Explorer",
                            _build_table(
                                ["Run", "Case", "Input", "Reason"],
                                [
                                    [
                                        run_id,
                                        case.case_index,
                                        case.input_text_snapshot[:80],
                                        case.failure_reason or "n/a",
                                    ]
                                    for case, run_id in failure_rows
                                ]
                                or [["No failing cases recorded.", "", "", ""]],
                            ),
                        ),
                        _build_card(
                            "Failure Clusters",
                            _build_badge_row(
                                [f"{cluster['title']} ({cluster['size']})" for cluster in latest_clusters],
                                empty_message="No failure clusters available yet.",
                            ),
                        ),
                        _build_card(
                            "Suggestions History",
                            _build_table(
                                ["Run", "Summary", "Model"],
                                [
                                    [run_id, suggestion.summary[:120], suggestion.model_name]
                                    for suggestion, run_id in suggestion_rows[:10]
                                ]
                                or [["No suggestions generated yet.", "", ""]],
                            ),
                        ),
                        _build_card(
                            "Dataset Inventory",
                            _build_table(
                                ["Dataset", "Version", "Cases"],
                                [
                                    [dataset.dataset_name, dataset.version_hash[:12], dataset.case_count]
                                    for dataset in datasets
                                ]
                                or [["No datasets yet.", "", ""]],
                            ),
                        ),
                        _build_card(
                            "Prompt Inventory",
                            _build_table(
                                ["Prompt", "Version", "Created"],
                                [
                                    [prompt.prompt_key, prompt.version, prompt.created_at.isoformat()]
                                    for prompt in prompts
                                ]
                                or [["No prompts yet.", "", ""]],
                            ),
                        ),
                    ],
                ),
            ],
        )

        prefab_app = PrefabApp(
            title="Eval_MCP Dashboard",
            theme=_dashboard_theme(),
            css_class="min-h-screen px-6 py-10 md:px-10",
            view=content,
        )
        return HTMLResponse(prefab_app.html(renderer_mode="bundled"))
