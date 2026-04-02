from __future__ import annotations

from collections import Counter
import json

import httpx

from core.config import get_settings
from core.errors import BackendError
from eval_backends.base import JudgeSuggestionResult


class GoogleJudgeRunner:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = get_settings()
        self.transport = transport

    async def generate_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str = "gemini-2.5-flash",
    ) -> JudgeSuggestionResult:
        if self.settings.effective_google_api_key:
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
            metadata={"model_name": model_name, "cluster_count": len(failure_clusters), "provider": "google-stub"},
        )

    async def _generate_live_suggestion(
        self,
        *,
        run_id: str,
        failure_clusters: list[dict],
        sample_inputs: list[str],
        model_name: str,
    ) -> JudgeSuggestionResult:
        api_key = self.settings.effective_google_api_key
        if not api_key:
            raise BackendError("Google API key is missing for live judge generation.", details={"provider": "google"})
        prompt = self._build_prompt(run_id=run_id, failure_clusters=failure_clusters, sample_inputs=sample_inputs)
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "You are an evaluation engineer. Return concise, actionable prompt-improvement guidance. "
                                "Respond as JSON with keys: summary, suggestion_text.\n\n"
                                f"{prompt}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 700,
                "responseMimeType": "application/json",
            },
        }
        async with httpx.AsyncClient(
            base_url=self.settings.google_api_base.rstrip("/"),
            timeout=self.settings.judge_request_timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"/v1beta/models/{model_name}:generateContent",
                params={"key": api_key},
                json=payload,
            )
        if response.is_error:
            raise BackendError(
                "Google judge request failed.",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )
        data = response.json()
        parts = []
        candidates = data.get("candidates") or []
        if candidates:
            parts = ((candidates[0].get("content") or {}).get("parts")) or []
        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        parsed = self._parse_response(content)
        return JudgeSuggestionResult(
            summary=parsed["summary"],
            suggestion_text=parsed["suggestion_text"],
            failure_clusters=[],
            metadata={"model_name": model_name, "cluster_count": len(failure_clusters), "provider": "google"},
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
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise BackendError("Google judge returned invalid JSON.", details={"body": response_text[:500]}) from exc
        summary = str(parsed.get("summary", "")).strip()
        suggestion_text = str(parsed.get("suggestion_text", "")).strip()
        if not summary or not suggestion_text:
            raise BackendError("Google judge response missing required fields.", details={"body": parsed})
        return {"summary": summary, "suggestion_text": suggestion_text}
