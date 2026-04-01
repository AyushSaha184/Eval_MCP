from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from eval_mcp.api_client import EvalMCPAPIClient, EvalMCPAPIError
from eval_mcp.cli import build_parser, main
from eval_mcp.config import get_mcp_settings
from eval_mcp.tool_handlers import get_run_status, register_golden_dataset


def test_cli_parser_supports_required_commands() -> None:
    parser = build_parser()

    command_args = {
        "serve": [],
        "api": [],
        "worker": [],
        "dashboard": [],
        "migrate": [],
        "register": ["--identifier", "user@example.com"],
        "create-api-key": ["--identifier", "user@example.com", "--onboarding-token", "token"],
        "create-project": ["--name", "Hosted Project"],
        "whoami": [],
        "list-api-keys": [],
        "revoke-api-key": ["key_123"],
    }
    for command, extra_args in command_args.items():
        parsed = parser.parse_args([command, *extra_args])
        assert parsed.command == command


def test_config_loading_from_env(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_MCP_API_URL", "https://example.invalid")
    monkeypatch.setenv("EVAL_MCP_API_KEY", "secret")
    monkeypatch.setenv("EVAL_MCP_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("EVAL_MCP_DEFAULT_PROJECT", "serena")
    get_mcp_settings.cache_clear()

    settings = get_mcp_settings()

    assert settings.api_url == "https://example.invalid"
    assert settings.api_key == "secret"
    assert settings.timeout_seconds == 12
    assert settings.default_project == "serena"

    get_mcp_settings.cache_clear()


@pytest.mark.asyncio
async def test_api_client_uses_backend_responses() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "dev-key"
        return httpx.Response(200, json={"ok": True, "status": "queued", "run_id": "run_123"})

    settings = get_mcp_settings()
    client = EvalMCPAPIClient(
        settings=settings.model_copy(
            update={"api_url": "http://testserver", "api_key": "dev-key"}
        ),
        transport=httpx.MockTransport(handler),
    )
    try:
        response = await client.get_run_status("run_123")
    finally:
        await client.aclose()

    assert response["run_id"] == "run_123"


@pytest.mark.asyncio
async def test_api_client_raises_structured_errors() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"detail": {"code": "unauthorized", "message": "Invalid API key.", "details": {}}},
        )

    client = EvalMCPAPIClient(
        settings=get_mcp_settings().model_copy(update={"api_url": "http://testserver"}),
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(EvalMCPAPIError) as exc_info:
            await client.list_projects()
    finally:
        await client.aclose()

    assert exc_info.value.code == "unauthorized"
    assert "Invalid API key." in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_handler_calls_http_backend() -> None:
    app = FastAPI()

    @app.post("/v1/datasets/register")
    async def register_dataset(payload: dict) -> dict:
        assert payload["dataset_name"] == "goldens"
        return {"ok": True, "dataset_name": payload["dataset_name"], "version_hash": "abc123", "case_count": 1}

    transport = httpx.ASGITransport(app=app)
    client = EvalMCPAPIClient(
        settings=get_mcp_settings().model_copy(update={"api_url": "http://testserver"}),
        transport=transport,
    )
    try:
        response = await register_golden_dataset(
            request=_dataset_registration(),
            client=client,
        )
    finally:
        await client.aclose()

    assert response["version_hash"] == "abc123"


def test_cli_dry_run_entrypoint() -> None:
    main(["serve", "--dry-run"])


def test_module_entrypoint_supports_dry_run() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    result = subprocess.run(
        [sys.executable, "-m", "eval_mcp", "serve", "--dry-run"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _dataset_registration():
    from domain.schemas import DatasetCaseInput, DatasetRegistration

    return DatasetRegistration(
        project="serena",
        dataset_name="goldens",
        cases=[DatasetCaseInput(input_text="hello", expected_output="world")],
    )
