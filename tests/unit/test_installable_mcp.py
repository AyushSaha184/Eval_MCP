from __future__ import annotations

import os
import subprocess
import sys
import builtins
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from eval_mcp.api_client import EvalMCPAPIClient, EvalMCPAPIError
from eval_mcp import cli as cli_module
from eval_mcp.cli import build_parser, main
from eval_mcp.config import get_mcp_settings
from eval_mcp.tool_handlers import register_golden_dataset


def test_cli_parser_supports_required_commands() -> None:
    parser = build_parser()

    command_args = {
        "serve": [],
        "api": [],
        "worker": [],
        "dashboard": [],
        "migrate": [],
        "register": ["--identifier", "user@example.com", "--password", "password123"],
        "login": ["--identifier", "user@example.com", "--password", "password123"],
        "create-api-key": ["--identifier", "user@example.com", "--onboarding-token", "token"],
        "create-project": ["--name", "Hosted Project"],
        "logout": [],
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


@pytest.mark.asyncio
async def test_login_command_blocks_cross_account_switch(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "load_local_config",
        lambda: {"identifier": "alice@example.com", "api_key": "emcp_existing_key"},
    )

    args = build_parser().parse_args(["login", "--email", "bob@example.com", "--password", "password123"])
    with pytest.raises(SystemExit) as exc_info:
        await cli_module._cmd_login(args)

    assert "already logged in with alice@example.com" in str(exc_info.value)


@pytest.mark.asyncio
async def test_login_command_stores_new_key(monkeypatch) -> None:
    saved: dict[str, str] = {}
    printed: list[str] = []

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def login_client(self, request: dict) -> dict:
            assert request["identifier"] == "alice@example.com"
            assert request["password"] == "password123"
            return {
                "identifier": "alice@example.com",
                "client_id": "client_1",
                "project_id": "project_1",
                "project_slug": "alice-default",
                "key_id": "key_1",
                "key_prefix": "emcp_abcd1234",
                "api_key": "emcp_abcd1234_secret",
                "label": request["label"],
            }

    monkeypatch.setattr(cli_module, "load_local_config", lambda: {})
    monkeypatch.setattr(cli_module, "save_local_config", lambda data: saved.update(data))
    monkeypatch.setattr(cli_module, "api_client", lambda: DummyClient())
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: printed.append(" ".join(str(arg) for arg in args)))

    args = build_parser().parse_args(["login", "--email", "alice@example.com", "--password", "password123"])
    await cli_module._cmd_login(args)

    assert saved["identifier"] == "alice@example.com"
    assert saved["api_key"] == "emcp_abcd1234_secret"
    assert any("Warning: store this API key securely." in line for line in printed)


def _dataset_registration():
    from domain.schemas import DatasetCaseInput, DatasetRegistration

    return DatasetRegistration(
        project="serena",
        dataset_name="goldens",
        cases=[DatasetCaseInput(input_text="hello", expected_output="world")],
    )
