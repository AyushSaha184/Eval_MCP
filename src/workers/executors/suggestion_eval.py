from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError
from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from db.repositories.suggestions import SuggestionsRepository
from eval_backends.judges.google_judge import GoogleJudgeRunner
from services.clustering import ClusteringService


class SuggestionEvalExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)
        self.metrics = MetricsRepository(session)
        self.suggestions = SuggestionsRepository(session)
        self.clustering = ClusteringService()
        self.judge = GoogleJudgeRunner()

    async def execute(self, run) -> None:
        snapshot = await self.runs.get_snapshot(run.id)
        if not snapshot:
            raise ValueError("No snapshot found for suggestion run")

        config = snapshot.runtime_config_snapshot_json or {}
        referenced_run_id = config.get("referenced_run_id")
        case_limit = config.get("case_limit", 20)
        cluster_limit = config.get("cluster_limit", 5)
        model_name = config.get("model_name", "gemini-2.5-flash")

        if not referenced_run_id:
            raise ValueError("Missing referenced_run_id in snapshot configuration")

        await self.runs.update_progress(
            run_db_id=run.id, processed_cases=0, total_cases=1
        )

        referenced_run = await self.runs.get_by_public_id(referenced_run_id)
        if not referenced_run:
            raise NotFoundError(f"Referenced run {referenced_run_id} was not found.")

        failed_cases = await self.metrics.get_failed_case_results(referenced_run.id)
        if not failed_cases:
            await self.suggestions.create(
                run_id=referenced_run.id,
                summary="No failed cases found in the referenced run.",
                suggestion_text="The referenced run has no failed cases to analyze. No improvement suggestions can be generated.",
                failure_clusters_json=[],
                model_name=model_name,
                metadata_json={
                    "suggestion_eval_run_id": run.run_id,
                    "referenced_run_id": referenced_run.run_id,
                    "skipped_reason": "no_failed_cases",
                },
            )
            await self.runs.finalize_success(
                run_db_id=run.id,
                pass_rate=None,
                processed_cases=1,
                total_cases=1,
            )
            return

        case_bundles = []
        for case_result in failed_cases[:case_limit]:
            case_metrics = await self.metrics.list_case_metrics(case_result.id)
            case_bundles.append({"case_result": case_result, "metrics": case_metrics})

        clusters = self.clustering.cluster_failed_cases(
            case_bundles, limit=cluster_limit
        )
        judge_result = await self.judge.generate_suggestion(
            run_id=referenced_run.run_id,
            failure_clusters=[cluster.model_dump(mode="json") for cluster in clusters],
            sample_inputs=[
                bundle["case_result"].input_text_snapshot for bundle in case_bundles[:3]
            ],
            model_name=model_name,
        )

        metadata = dict(judge_result.metadata)
        metadata["suggestion_eval_run_id"] = run.run_id
        metadata["referenced_run_id"] = referenced_run.run_id
        await self.suggestions.create(
            run_id=referenced_run.id,
            summary=judge_result.summary,
            suggestion_text=judge_result.suggestion_text,
            failure_clusters_json=[
                cluster.model_dump(mode="json") for cluster in clusters
            ],
            model_name=model_name,
            metadata_json=metadata,
        )

        await self.runs.finalize_success(
            run_db_id=run.id,
            pass_rate=None,
            processed_cases=1,
            total_cases=1,
        )
