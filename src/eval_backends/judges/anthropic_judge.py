from __future__ import annotations

from collections import Counter

import httpx

from core.config import get_settings
from core.errors import BackendError
from eval_backends.base import JudgeSuggestionResult


class AnthropicJudgeRunner:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = get_settings()
        self.transport = transport

    async def generate_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str = "anthropic-stub-judge",
    ) -> JudgeSuggestionResult:
        if self.settings.anthropic_api_key:
            return await self._generate_live_suggestion(
                run_id=run_id,
                failure_clusters=failure_clusters,
                sample_inputs=sample_inputs,
                model_name=model_name,
            )
        return self._generate_stub_suggestion(
            run_id=run_id,
            failure_clusters=failure_clusters,
            sample_inputs=sample_inputs,
            model_name=model_name,
        )

    def _generate_stub_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str,
    ) -> JudgeSuggestionResult:
        cluster_titles = [cluster["title"] for cluster in failure_clusters]
        most_common = Counter(cluster_titles).most_common(1)
        dominant = most_common[0][0] if most_common else "mixed quality failures"
        summary = f"Run {run_id} shows repeated issues around {dominant}."
        bullets = [
            "Tighten the system prompt to demand grounded, directly comparable outputs.",
            "Add explicit formatting examples for the highest-volume failure cluster.",
            "Review failing cases with the strongest regressions before expanding the prompt scope.",
        ]
        if sample_inputs:
            bullets.append(f"Representative failing input: {sample_inputs[0]}")
        return JudgeSuggestionResult(
            summary=summary,
            suggestion_text="\n".join(f"- {line}" for line in bullets),
            failure_clusters=[],
            metadata={"model_name": model_name, "cluster_count": len(failure_clusters)},
        )

    async def _generate_live_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str,
    ) -> JudgeSuggestionResult:
        prompt = self._build_prompt(run_id=run_id, failure_clusters=failure_clusters, sample_inputs=sample_inputs)
        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": self.settings.anthropic_api_version,
        }
        payload = {
            "model": model_name,
            "max_tokens": 700,
            "temperature": 0.2,
            "system": (
                "You are an evaluation engineer. Return concise, actionable prompt-improvement guidance. "
                "Respond as JSON with keys: summary, suggestion_text."
            ),
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(
            base_url=self.settings.anthropic_api_base.rstrip("/"),
            timeout=self.settings.judge_request_timeout_seconds,
            headers=headers,
            transport=self.transport,
        ) as client:
            response = await client.post("/v1/messages", json=payload)
        if response.is_error:
            raise BackendError(
                "Anthropic judge request failed.",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )
        data = response.json()
        content = "".join(part.get("text", "") for part in (data.get("content") or []) if isinstance(part, dict)).strip()
        parsed = self._parse_response(content)
        return JudgeSuggestionResult(
            summary=parsed["summary"],
            suggestion_text=parsed["suggestion_text"],
            failure_clusters=[],
            metadata={"model_name": model_name, "cluster_count": len(failure_clusters), "provider": "anthropic"},
        )

    def _build_prompt(self, *, run_id: str, failure_clusters: list[dict], sample_inputs: list[str]) -> str:
        return (
            f"Run ID: {run_id}\n"
            f"Failure clusters: {failure_clusters}\n"
            f"Sample inputs: {sample_inputs}\n\n"
            "Return JSON with:\n"
            '- "summary": one sentence\n'
            '- "suggestion_text": 3-6 bullet points as plain text'
        )

    def _parse_response(self, response_text: str) -> dict[str, str]:
        import json

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise BackendError("Anthropic judge returned invalid JSON.", details={"body": response_text[:500]}) from exc
        summary = str(parsed.get("summary", "")).strip()
        suggestion_text = str(parsed.get("suggestion_text", "")).strip()
        if not summary or not suggestion_text:
            raise BackendError("Anthropic judge response missing required fields.", details={"body": parsed})
        return {"summary": summary, "suggestion_text": suggestion_text}
