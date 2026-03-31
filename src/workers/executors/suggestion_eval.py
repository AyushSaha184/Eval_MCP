from __future__ import annotations

from eval_backends.judges.anthropic_judge import AnthropicJudgeRunner


class SuggestionEvalExecutor:
    def __init__(self) -> None:
        self.judge = AnthropicJudgeRunner()

    async def execute(self, *, run_id: str, failure_clusters: list[dict], sample_inputs: list[str]):
        return await self.judge.generate_suggestion(
            run_id=run_id,
            failure_clusters=failure_clusters,
            sample_inputs=sample_inputs,
        )

