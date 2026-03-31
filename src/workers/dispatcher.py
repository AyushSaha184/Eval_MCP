from __future__ import annotations

from core.errors import RunExecutionError
from domain.enums import RunType
from workers.executors.prompt_eval import PromptEvalExecutor
from workers.executors.rag_eval import RAGEvalExecutor


class RunDispatcher:
    def __init__(self, session) -> None:
        self.session = session

    async def dispatch(self, run) -> None:
        if run.run_type in {RunType.PROMPT_EVAL, RunType.COMPARISON_BACKING_RUN}:
            await PromptEvalExecutor(self.session).execute(run)
            return
        if run.run_type == RunType.RAG_EVAL:
            await RAGEvalExecutor(self.session).execute(run)
            return
        raise RunExecutionError(f"Unsupported run type `{run.run_type}`.")

