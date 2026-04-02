from __future__ import annotations

import httpx
import pytest

from core.config import get_settings
from eval_backends.judges.google_judge import GoogleJudgeRunner
from eval_backends.llm_runner import LLMRunner


@pytest.mark.asyncio
async def test_google_llm_runner_live_path(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_AI_STUDIO_API_KEY", "google-test-key")
    get_settings.cache_clear()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "google-test-key"
        assert request.url.path.endswith(":generateContent")
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Paris"}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2, "totalTokenCount": 12},
            },
        )

    runner = LLMRunner(transport=httpx.MockTransport(handler))
    result = await runner.generate(
        prompt_snapshot={"content": "Answer the question: {input}"},
        input_text="Capital of France?",
        expected_output="Paris",
        model_config={"provider": "google", "model_name": "gemini-2.5-flash"},
        runtime_config={},
    )

    assert result.output_text == "Paris"
    assert result.metadata["provider"] == "google"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_google_judge_live_path(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_AI_STUDIO_API_KEY", "google-test-key")
    get_settings.cache_clear()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "google-test-key"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"summary":"Failures cluster around grounding.","suggestion_text":"- Add grounding instructions\\n- Add explicit retrieval usage\\n- Tighten answer format"}'
                                }
                            ]
                        }
                    }
                ]
            },
        )

    runner = GoogleJudgeRunner(transport=httpx.MockTransport(handler))
    result = await runner.generate_suggestion(
        run_id="run_123",
        failure_clusters=[{"title": "Grounding gaps", "size": 3}],
        sample_inputs=["What is the refund policy?"],
        model_name="gemini-2.5-flash",
    )

    assert "grounding" in result.summary.lower()
    assert "Add grounding instructions" in result.suggestion_text
    get_settings.cache_clear()


def test_api_key_rotation_parses_multiple_keys(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_MCP_API_KEY", "new-key")
    monkeypatch.setenv("EVAL_MCP_API_KEYS", "old-key-1, old-key-2")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.valid_api_keys == ["new-key", "old-key-1", "old-key-2"]
    get_settings.cache_clear()


def test_b2_storage_envs_are_exposed_via_object_storage_properties(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "b2")
    monkeypatch.setenv("B2_BUCKET", "eval-artifacts")
    monkeypatch.setenv("B2_REGION", "us-west-004")
    monkeypatch.setenv("B2_ENDPOINT_URL", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setenv("B2_KEY_ID", "b2-key-id")
    monkeypatch.setenv("B2_APPLICATION_KEY", "b2-application-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.storage_provider == "b2"
    assert settings.object_storage_bucket == "eval-artifacts"
    assert settings.object_storage_region == "us-west-004"
    assert settings.object_storage_endpoint_url == "https://s3.us-west-004.backblazeb2.com"
    assert settings.object_storage_access_key_id == "b2-key-id"
    assert settings.object_storage_secret_access_key == "b2-application-key"
    get_settings.cache_clear()
