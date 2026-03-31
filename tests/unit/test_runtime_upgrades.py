from __future__ import annotations

import httpx
import pytest

from core.config import get_settings
from eval_backends.judges.anthropic_judge import AnthropicJudgeRunner
from eval_backends.llm_runner import LLMRunner


@pytest.mark.asyncio
async def test_openai_llm_runner_live_path(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    get_settings.cache_clear()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer openai-test-key"
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Paris"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            },
        )

    runner = LLMRunner(transport=httpx.MockTransport(handler))
    result = await runner.generate(
        prompt_snapshot={"content": "Answer the question: {input}"},
        input_text="Capital of France?",
        expected_output="Paris",
        model_config={"provider": "openai", "model_name": "gpt-4o-mini"},
        runtime_config={},
    )

    assert result.output_text == "Paris"
    assert result.metadata["provider"] == "openai"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_anthropic_judge_live_path(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    get_settings.cache_clear()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "anthropic-test-key"
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": '{"summary":"Failures cluster around grounding.","suggestion_text":"- Add grounding instructions\\n- Add explicit retrieval usage\\n- Tighten answer format"}',
                    }
                ]
            },
        )

    runner = AnthropicJudgeRunner(transport=httpx.MockTransport(handler))
    result = await runner.generate_suggestion(
        run_id="run_123",
        failure_clusters=[{"title": "Grounding gaps", "size": 3}],
        sample_inputs=["What is the refund policy?"],
        model_name="claude-3-5-sonnet-latest",
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
