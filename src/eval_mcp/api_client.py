from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import httpx

from eval_mcp.config import MCPClientSettings, get_mcp_settings
from eval_mcp.local_config import load_local_config

logger = logging.getLogger(__name__)

# FIX(security): Endpoints that do NOT require an API key.
# Auth-related endpoints use credentials in the request body, not headers.
_PUBLIC_ENDPOINTS: frozenset[str] = frozenset({
    "/v1/auth/register",
    "/v1/auth/login",
})

# FIX(security): Allowed API URL hostnames.
# Only trusted first-party hosts may receive the API key header.
_TRUSTED_API_HOSTS: frozenset[str] = frozenset({
    "eval-mcp.onrender.com",
    "localhost",
    "127.0.0.1",
    "testserver",
})

# FIX(memory): Maximum response body size in bytes (10 MiB).
# Prevents OOM from unexpectedly large payloads.
_MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024

# FIX(resilience): Retry configuration for transient failures.
_MAX_RETRIES: int = 3
_RETRY_BACKOFF_BASE: float = 0.5  # seconds; doubles each attempt
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({502, 503, 504, 429})


class EvalMCPAPIError(RuntimeError):
    def __init__(self, message: str, *, code: str = "api_error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _is_trusted_host(url: str) -> bool:
    """Check whether the API URL points to a trusted host."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return hostname in _TRUSTED_API_HOSTS


class EvalMCPAPIClient:
    """HTTP client for the Eval MCP backend API.

    FIX(concurrency): This client is designed to be instantiated ONCE and
    reused across the MCP server's lifetime, enabling proper connection
    pooling via httpx's built-in pool. Use the module-level
    ``get_shared_client()`` / ``close_shared_client()`` helpers or the
    ``api_client()`` context manager for lifecycle-safe access.
    """

    def __init__(
        self,
        *,
        settings: MCPClientSettings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_mcp_settings()
        local_cfg = load_local_config()

        self._effective_api_key: str | None = self.settings.api_key or local_cfg.get("api_key")

        # FIX(security): Only embed the API key in default headers when the
        # base URL points to a trusted host.  Per-request header injection
        # is handled in ``_request()`` so the key is never sent to public
        # auth endpoints or untrusted hosts.
        self._base_url: str = self.settings.api_url.rstrip("/")
        self._host_trusted: bool = _is_trusted_host(self._base_url)
        if not self._host_trusted and self._effective_api_key:
            logger.warning(
                "API URL '%s' is not in the trusted host list. "
                "API key will NOT be attached to requests.",
                self._base_url,
            )

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self.settings.timeout_seconds,
            # FIX(security): Headers are injected per-request, NOT globally.
            transport=transport,
        )

    async def __aenter__(self) -> "EvalMCPAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers_for(self, path: str) -> dict[str, str]:
        """Build request-specific headers.

        FIX(security): The API key is only included when:
          1. The base URL points to a trusted host, AND
          2. The endpoint is not a public auth endpoint.
        """
        headers: dict[str, str] = {}
        if (
            self._effective_api_key
            and self._host_trusted
            and path not in _PUBLIC_ENDPOINTS
        ):
            headers["x-api-key"] = self._effective_api_key
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> dict:
        """Execute an HTTP request with retry and response-size safety.

        FIX(resilience): Retries on transient 5xx / 429 errors and
        connection-level failures using exponential backoff.

        FIX(memory): Rejects responses larger than ``_MAX_RESPONSE_BYTES``.
        """
        headers = self._headers_for(path)
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.request(
                    method, path, params=params, json=json, headers=headers,
                )
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        "Request to %s failed (attempt %d/%d): %s — retrying in %.1fs",
                        path, attempt + 1, _MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise EvalMCPAPIError(
                    f"Backend unreachable after {_MAX_RETRIES} attempts: {exc}",
                    code="connection_error",
                ) from exc

            # FIX(resilience): Retry on transient server errors.
            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Received %d from %s (attempt %d/%d) — retrying in %.1fs",
                    response.status_code, path, attempt + 1, _MAX_RETRIES, wait,
                )
                await asyncio.sleep(wait)
                continue

            # FIX(memory): Reject oversized responses before parsing.
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > _MAX_RESPONSE_BYTES:
                raise EvalMCPAPIError(
                    f"Response too large ({content_length} bytes, max {_MAX_RESPONSE_BYTES}).",
                    code="response_too_large",
                )
            raw = response.content
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise EvalMCPAPIError(
                    f"Response too large ({len(raw)} bytes, max {_MAX_RESPONSE_BYTES}).",
                    code="response_too_large",
                )

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

        # Fallback — should not be reached, but guard against logic errors.
        raise EvalMCPAPIError(  # pragma: no cover
            f"Request to {path} failed after {_MAX_RETRIES} attempts.",
            code="max_retries_exceeded",
        )

    # --- Endpoint methods (unchanged signatures) ---

    async def list_projects(self) -> dict:
        return await self._request("GET", "/v1/projects")

    async def register_client(self, request: dict) -> dict:
        return await self._request("POST", "/v1/auth/register", json=request)

    async def create_api_key(self, request: dict) -> dict:
        return await self._request("POST", "/v1/auth/api-keys", json=request)

    async def login_client(self, request: dict) -> dict:
        return await self._request("POST", "/v1/auth/login", json=request)

    async def create_api_key_for_current_client(self, request: dict) -> dict:
        return await self._request("POST", "/v1/auth/api-keys/current", json=request)

    async def create_project_for_current_client(self, request: dict) -> dict:
        return await self._request("POST", "/v1/auth/projects", json=request)

    async def whoami(self) -> dict:
        return await self._request("GET", "/v1/auth/whoami")

    async def list_api_keys(self) -> dict:
        return await self._request("GET", "/v1/auth/api-keys")

    async def revoke_api_key(self, key_id: str) -> dict:
        return await self._request("POST", f"/v1/auth/api-keys/{key_id}/revoke")

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

    async def get_latest_suggestion(self, run_id: str) -> dict:
        return await self._request("GET", f"/v1/runs/{run_id}/suggestions/latest")

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


# ---------------------------------------------------------------------------
# FIX(concurrency): Global shared client singleton.
# Reuses one httpx.AsyncClient across all tool invocations, eliminating
# per-request TLS handshakes and ephemeral port exhaustion.
# ---------------------------------------------------------------------------
_shared_client: EvalMCPAPIClient | None = None
_shared_client_lock = asyncio.Lock()


async def get_shared_client(
    *,
    settings: MCPClientSettings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> EvalMCPAPIClient:
    """Return (and lazily create) a process-wide ``EvalMCPAPIClient``."""
    global _shared_client
    async with _shared_client_lock:
        if _shared_client is None:
            _shared_client = EvalMCPAPIClient(settings=settings, transport=transport)
    return _shared_client


async def close_shared_client() -> None:
    """Shut down the global client (call during server teardown)."""
    global _shared_client
    async with _shared_client_lock:
        if _shared_client is not None:
            await _shared_client.aclose()
            _shared_client = None


def reset_shared_client() -> None:
    """Non-async reset for test isolation (sets the singleton to None)."""
    global _shared_client
    _shared_client = None


@asynccontextmanager
async def api_client(
    *,
    settings: MCPClientSettings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
):
    """Context manager for one-off or test usage.

    For production MCP tool handlers, prefer ``get_shared_client()`` to
    avoid creating a new ``httpx.AsyncClient`` on every invocation.
    """
    client = EvalMCPAPIClient(settings=settings, transport=transport)
    try:
        yield client
    finally:
        await client.aclose()
