from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError
from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from db.repositories.suggestions import SuggestionsRepository
from domain.schemas import SuggestFixRequest, SuggestionResponse
from eval_backends.judges.anthropic_judge import AnthropicJudgeRunner
from services.clustering import ClusteringService


class SuggestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)
        self.metrics = MetricsRepository(session)
        self.suggestions = SuggestionsRepository(session)
        self.clustering = ClusteringService()
        self.judge = AnthropicJudgeRunner()

    async def suggest_fix(self, request: SuggestFixRequest) -> SuggestionResponse:
        run = await self.runs.get_by_public_id(request.run_id)
        if run is None:
            raise NotFoundError(f"Run `{request.run_id}` was not found.")

        failed_cases = await self.metrics.get_failed_case_results(run.id)
        case_bundles = []
        for case_result in failed_cases[: request.case_limit]:
            case_metrics = await self.metrics.list_case_metrics(case_result.id)
            case_bundles.append({"case_result": case_result, "metrics": case_metrics})
        clusters = self.clustering.cluster_failed_cases(case_bundles, limit=request.cluster_limit)
        judge_result = await self.judge.generate_suggestion(
            run_id=run.run_id,
            failure_clusters=[cluster.model_dump(mode="json") for cluster in clusters],
            sample_inputs=[bundle["case_result"].input_text_snapshot for bundle in case_bundles[:3]],
            model_name=request.model_name or "anthropic-stub-judge",
        )
        suggestion = await self.suggestions.create(
            run_id=run.id,
            summary=judge_result.summary,
            suggestion_text=judge_result.suggestion_text,
            failure_clusters_json=[cluster.model_dump(mode="json") for cluster in clusters],
            model_name=request.model_name or "anthropic-stub-judge",
            metadata_json=judge_result.metadata,
        )
        return SuggestionResponse(
            id=suggestion.id,
            run_id=run.run_id,
            summary=suggestion.summary,
            suggestion_text=suggestion.suggestion_text,
            failure_clusters=clusters,
            model_name=suggestion.model_name,
            created_at=suggestion.created_at,
        )

