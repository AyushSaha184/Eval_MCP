from __future__ import annotations

import time
from hashlib import sha256
from typing import Any

import httpx

from core.config import get_settings
from core.errors import BackendError
from eval_backends.base import GenerationResult


def _render_prompt(prompt_snapshot: dict[str, Any], input_text: str) -> str:
    content = prompt_snapshot.get("content", "")
    rendered = content.replace("{input}", input_text).replace("{query}", input_text)
    if rendered == content:
        rendered = f"{content}\n\nInput:\n{input_text}".strip()
    return rendered


class LLMRunner:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = get_settings()
        self.transport = transport

    async def generate(
        self,
        *,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        expected_output: str | None,
        model_config: dict[str, Any],
        runtime_config: dict[str, Any],
        retrieved_context: list[str] | None = None,
    ) -> GenerationResult:
        provider = model_config.get("provider", self.settings.default_model_provider).lower()
        if provider == "stub":
            return self._generate_stub(
                prompt_snapshot=prompt_snapshot,
                input_text=input_text,
                expected_output=expected_output,
                model_config=model_config,
                runtime_config=runtime_config,
                retrieved_context=retrieved_context,
            )
        if provider == "openai":
            return await self._generate_openai(
                prompt_snapshot=prompt_snapshot,
                input_text=input_text,
                model_config=model_config,
                runtime_config=runtime_config,
                retrieved_context=retrieved_context or [],
            )
        if provider == "anthropic":
            return await self._generate_anthropic(
                prompt_snapshot=prompt_snapshot,
                input_text=input_text,
                model_config=model_config,
                runtime_config=runtime_config,
                retrieved_context=retrieved_context or [],
            )
        raise BackendError(
            message=f"Model provider `{provider}` is not implemented yet.",
            details={"provider": provider},
        )

    def _generate_stub(
        self,
        *,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        expected_output: str | None,
        model_config: dict[str, Any],
        runtime_config: dict[str, Any],
        retrieved_context: list[str] | None,
    ) -> GenerationResult:
        rendered_prompt = _render_prompt(prompt_snapshot, input_text)
        actual_output = self._stub_output(
            rendered_prompt=rendered_prompt,
            prompt_snapshot=prompt_snapshot,
            input_text=input_text,
            expected_output=expected_output,
            retrieved_context=retrieved_context or [],
            model_config=model_config,
        )
        token_usage = {
            "prompt_tokens": max(1, len(rendered_prompt.split())),
            "completion_tokens": max(1, len(actual_output.split())),
        }
        return GenerationResult(
            output_text=actual_output,
            rendered_prompt=rendered_prompt,
            latency_ms=5,
            token_usage=token_usage,
            retrieved_context=retrieved_context or [],
            metadata={"provider": "stub", "runtime": runtime_config},
        )

    def _build_messages(
        self,
        *,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        retrieved_context: list[str],
    ) -> tuple[str | None, str]:
        system_prompt = prompt_snapshot.get("system_prompt")
        rendered_prompt = _render_prompt(prompt_snapshot, input_text)
        if retrieved_context:
            context_block = "\n".join(f"- {chunk}" for chunk in retrieved_context)
            rendered_prompt = f"{rendered_prompt}\n\nRetrieved context:\n{context_block}"
        return system_prompt, rendered_prompt

    async def _generate_openai(
        self,
        *,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        model_config: dict[str, Any],
        runtime_config: dict[str, Any],
        retrieved_context: list[str],
    ) -> GenerationResult:
        if not self.settings.openai_api_key:
            raise BackendError("OPENAI_API_KEY is required for provider `openai`.", details={"provider": "openai"})
        system_prompt, rendered_prompt = self._build_messages(
            prompt_snapshot=prompt_snapshot,
            input_text=input_text,
            retrieved_context=retrieved_context,
        )
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        if self.settings.openai_organization:
            headers["OpenAI-Organization"] = self.settings.openai_organization
        payload = {
            "model": model_config.get("model_name", self.settings.default_model_name),
            "messages": ([{"role": "system", "content": system_prompt}] if system_prompt else [])
            + [{"role": "user", "content": rendered_prompt}],
            "temperature": model_config.get("temperature", 0.0),
            "max_tokens": model_config.get("max_tokens", 512),
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.settings.openai_api_base.rstrip("/"),
            timeout=self.settings.model_request_timeout_seconds,
            headers=headers,
            transport=self.transport,
        ) as client:
            response = await client.post("/chat/completions", json=payload)
        if response.is_error:
            raise BackendError(
                "OpenAI generation request failed.",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            output_text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            output_text = content or ""
        usage = data.get("usage") or {}
        return GenerationResult(
            output_text=output_text.strip(),
            rendered_prompt=rendered_prompt,
            latency_ms=int((time.perf_counter() - start) * 1000),
            token_usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            retrieved_context=retrieved_context,
            metadata={"provider": "openai", "model": payload["model"], "runtime": runtime_config},
        )

    async def _generate_anthropic(
        self,
        *,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        model_config: dict[str, Any],
        runtime_config: dict[str, Any],
        retrieved_context: list[str],
    ) -> GenerationResult:
        if not self.settings.anthropic_api_key:
            raise BackendError(
                "ANTHROPIC_API_KEY is required for provider `anthropic`.",
                details={"provider": "anthropic"},
            )
        system_prompt, rendered_prompt = self._build_messages(
            prompt_snapshot=prompt_snapshot,
            input_text=input_text,
            retrieved_context=retrieved_context,
        )
        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": self.settings.anthropic_api_version,
        }
        payload = {
            "model": model_config.get("model_name", self.settings.default_model_name),
            "max_tokens": model_config.get("max_tokens", 512),
            "temperature": model_config.get("temperature", 0.0),
            "messages": [{"role": "user", "content": rendered_prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        start = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.settings.anthropic_api_base.rstrip("/"),
            timeout=self.settings.model_request_timeout_seconds,
            headers=headers,
            transport=self.transport,
        ) as client:
            response = await client.post("/v1/messages", json=payload)
        if response.is_error:
            raise BackendError(
                "Anthropic generation request failed.",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )
        data = response.json()
        parts = data.get("content") or []
        output_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        usage = data.get("usage") or {}
        return GenerationResult(
            output_text=output_text.strip(),
            rendered_prompt=rendered_prompt,
            latency_ms=int((time.perf_counter() - start) * 1000),
            token_usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
            },
            retrieved_context=retrieved_context,
            metadata={"provider": "anthropic", "model": payload["model"], "runtime": runtime_config},
        )

    def _stub_output(
        self,
        *,
        rendered_prompt: str,
        prompt_snapshot: dict[str, Any],
        input_text: str,
        expected_output: str | None,
        retrieved_context: list[str],
        model_config: dict[str, Any],
    ) -> str:
        prompt_content = f"{prompt_snapshot.get('system_prompt', '')} {prompt_snapshot.get('content', '')}".lower()
        quality = 0.75
        if any(token in prompt_content for token in ("bad", "degrade", "weak", "unsafe")):
            quality = 0.25
        elif any(token in prompt_content for token in ("good", "improve", "strong", "grounded")):
            quality = 0.95
        if model_config.get("extra", {}).get("mode") == "perfect":
            quality = 1.0
        if model_config.get("extra", {}).get("mode") == "noisy":
            quality = 0.35

        digest = int(sha256(rendered_prompt.encode("utf-8")).hexdigest(), 16)
        if expected_output and quality >= 0.9:
            return expected_output
        if expected_output and quality >= 0.6:
            return expected_output if digest % 5 else f"{expected_output} (draft)"
        if expected_output:
            return f"uncertain: {input_text}"
        if retrieved_context:
            return retrieved_context[0]
        return f"stub-response: {input_text}"
