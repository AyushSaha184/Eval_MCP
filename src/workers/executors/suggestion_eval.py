from __future__ import annotations

from eval_backends.judges.google_judge import GoogleJudgeRunner


class SuggestionEvalExecutor:
    def __init__(self) -> None:
        self.judge = GoogleJudgeRunner()

    async def execute(self, *, run_id: str, failure_clusters: list[dict], sample_inputs: list[str]):
        return await self.judge.generate_suggestion(
            run_id=run_id,
            failure_clusters=failure_clusters,
            sample_inputs=sample_inputs,
        )
