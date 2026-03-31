from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx

from eval_mcp.config import MCPClientSettings, get_mcp_settings


class EvalMCPAPIError(RuntimeError):
    def __init__(self, message: str, *, code: str = "api_error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class EvalMCPAPIClient:
    def __init__(
        self,
        *,
        settings: MCPClientSettings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_mcp_settings()
        headers: dict[str, str] = {}
        if self.settings.api_key:
            headers["x-api-key"] = self.settings.api_key
        self._client = httpx.AsyncClient(
            base_url=self.settings.api_url.rstrip("/"),
            timeout=self.settings.timeout_seconds,
            headers=headers,
            transport=transport,
        )

    async def __aenter__(self) -> "EvalMCPAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> dict:
        response = await self._client.request(method, path, params=params, json=json)
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise EvalMCPAPIError(
                "Backend API returned a non-JSON response.",
                code="invalid_api_response",
                details={"status_code": response.status_code},
            ) from exc
        if response.is_error:
            payload_dict = payload if isinstance(payload, dict) else {}
            detail = payload_dict.get("detail")
            message = payload_dict.get("message") or (
                detail.get("message") if isinstance(detail, dict) else detail
            ) or response.reason_phrase
            details = payload_dict.get("details") or (
                detail.get("details") if isinstance(detail, dict) else {}
            )
            code = payload_dict.get("code") or (detail.get("code") if isinstance(detail, dict) else None) or "api_error"
            raise EvalMCPAPIError(message, code=code, details=details)
        if isinstance(payload, dict) and payload.get("ok") is False:
            error = payload.get("error") or {}
            raise EvalMCPAPIError(
                error.get("message", "Backend API request failed."),
                code=error.get("code", "api_error"),
                details=error.get("details") or {},
            )
        return payload

    async def list_projects(self) -> dict:
        return await self._request("GET", "/v1/projects")

    async def list_datasets(self, project: str) -> dict:
        return await self._request("GET", f"/v1/projects/{project}/datasets")

    async def list_prompts(self, project: str) -> dict:
        return await self._request("GET", f"/v1/projects/{project}/prompts")

    async def register_golden_dataset(self, request: dict) -> dict:
        return await self._request("POST", "/v1/datasets/register", json=request)

    async def run_eval_suite(self, request: dict) -> dict:
        return await self._request("POST", "/v1/runs/eval", json=request)

    async def score_rag_pipeline(self, request: dict) -> dict:
        return await self._request("POST", "/v1/runs/rag", json=request)

    async def compare_prompt_versions(self, request: dict) -> dict:
        return await self._request("POST", "/v1/comparisons/prompt-versions", json=request)

    async def detect_regression(self, request: dict) -> dict:
        return await self._request("POST", "/v1/regressions/detect", json=request)

    async def suggest_fix(self, request: dict) -> dict:
        return await self._request("POST", "/v1/suggestions", json=request)

    async def get_eval_history(self, request: dict) -> dict:
        return await self._request("POST", "/v1/history/query", json=request)

    async def get_run_status(self, run_id: str) -> dict:
        return await self._request("GET", f"/v1/runs/{run_id}/status")

    async def set_baseline_run(self, request: dict) -> dict:
        return await self._request("POST", "/v1/baselines/set", json=request)

    async def rerun_failed_cases(self, request: dict) -> dict:
        return await self._request("POST", "/v1/runs/rerun-failed", json=request)

    async def annotate_run(self, request: dict) -> dict:
        return await self._request("POST", "/v1/runs/annotate", json=request)

    async def get_supported_metrics(self) -> dict:
        return await self._request("GET", "/v1/meta/supported-metrics")


@asynccontextmanager
async def api_client(
    *,
    settings: MCPClientSettings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
):
    client = EvalMCPAPIClient(settings=settings, transport=transport)
    try:
        yield client
    finally:
        await client.aclose()
