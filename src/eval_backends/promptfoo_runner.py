from __future__ import annotations

from core.errors import BackendError


class PromptfooRunner:
    async def build_report(self, *args, **kwargs) -> dict:
        raise BackendError(
            message="Promptfoo compatibility is not implemented yet.",
            details={"backend": "promptfoo"},
        )

