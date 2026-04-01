from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence

from core.config import get_settings
from eval_mcp.api_client import api_client
from eval_mcp.config import get_mcp_settings
from eval_mcp.local_config import load_local_config, save_local_config
from eval_mcp.mcp_server import run_server
from eval_mcp_server.runtime import run_api, run_dashboard, run_migrations, run_worker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eval-mcp", description="Eval MCP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Start the MCP stdio server.")
    serve.add_argument("--dry-run", action="store_true", help="Validate configuration without starting stdio.")

    settings = get_settings()

    api = subparsers.add_parser("api", help="Start the backend HTTP API.")
    api.add_argument("--host", default=settings.api_host)
    api.add_argument("--port", type=int, default=settings.api_port)

    worker = subparsers.add_parser("worker", help="Start the backend worker loop.")
    worker.add_argument("--max-runs", type=int, default=None)

    dashboard = subparsers.add_parser("dashboard", help="Start the read-only dashboard.")
    dashboard.add_argument("--host", default=settings.dashboard_host)
    dashboard.add_argument("--port", type=int, default=settings.dashboard_port)

    migrate = subparsers.add_parser("migrate", help="Run Alembic migrations.")
    migrate.add_argument("revision", nargs="?", default="head")

    register = subparsers.add_parser("register", help="Register a hosted account and default project.")
    register.add_argument("--identifier", default=None, help="Email or username used for registration.")
    register.add_argument("--email", default=None, help="Email alias for --identifier.")
    register.add_argument("--username", default=None, help="Username alias for --identifier.")
    register.add_argument("--display-name", default=None, help="Optional display name.")

    create_key = subparsers.add_parser("create-api-key", help="Create a scoped API key for IDE MCP usage.")
    create_key.add_argument("--identifier", default=None, help="Registration identifier (email or username).")
    create_key.add_argument("--onboarding-token", default=None, help="Onboarding token from register output.")
    create_key.add_argument("--label", default=None, help="Optional key label.")
    create_key.add_argument("--project", default=None, help="Optional project slug/id to scope the key.")

    create_project = subparsers.add_parser("create-project", help="Create a hosted project under the current account.")
    create_project.add_argument("--name", required=True, help="Project display name.")
    create_project.add_argument("--slug", default=None, help="Optional project slug.")
    create_project.add_argument("--description", default=None, help="Optional project description.")

    subparsers.add_parser("whoami", help="Validate the current API key and print scoped identity.")
    subparsers.add_parser("list-api-keys", help="List DB-backed API keys for your account.")
    revoke_key = subparsers.add_parser("revoke-api-key", help="Revoke an API key by id.")
    revoke_key.add_argument("key_id", help="The API key id to revoke.")

    return parser


def _resolve_identifier(args: argparse.Namespace, local_cfg: dict) -> str | None:
    return args.identifier or args.email or args.username or local_cfg.get("identifier")


async def _cmd_register(args: argparse.Namespace) -> None:
    local_cfg = load_local_config()
    identifier = _resolve_identifier(args, local_cfg)
    if not identifier:
        raise SystemExit("Provide --identifier (or --email / --username) for registration.")

    async with api_client() as client:
        response = await client.register_client(
            {
                "identifier": identifier,
                "display_name": args.display_name,
            }
        )

    local_cfg.update(
        {
            "identifier": response["identifier"],
            "display_name": response.get("display_name"),
            "client_id": response["client_id"],
            "project_id": response["project_id"],
            "project_slug": response["project_slug"],
            "onboarding_token": response["onboarding_token"],
            "api_url": get_mcp_settings().api_url,
        }
    )
    save_local_config(local_cfg)

    print("Registration complete.")
    print(json.dumps({
        "identifier": response["identifier"],
        "client_id": response["client_id"],
        "project_slug": response["project_slug"],
        "created": response["created"],
    }, indent=2))
    print("Next step: eval-mcp create-api-key")


async def _cmd_create_api_key(args: argparse.Namespace) -> None:
    local_cfg = load_local_config()
    identifier = _resolve_identifier(args, local_cfg)
    onboarding_token = args.onboarding_token or local_cfg.get("onboarding_token")
    existing_api_key = get_mcp_settings().api_key or local_cfg.get("api_key")

    async with api_client() as client:
        if onboarding_token:
            if not identifier:
                raise SystemExit("Missing identifier. Run eval-mcp register or pass --identifier.")
            response = await client.create_api_key(
                {
                    "identifier": identifier,
                    "onboarding_token": onboarding_token,
                    "label": args.label,
                    "project": args.project,
                }
            )
        else:
            if not existing_api_key:
                raise SystemExit(
                    "Missing onboarding token and current API key. Run eval-mcp register first or set EVAL_MCP_API_KEY."
                )
            response = await client.create_api_key_for_current_client(
                {
                    "label": args.label,
                    "project": args.project,
                }
            )

    local_cfg.update(
        {
            "identifier": response["identifier"],
            "client_id": response["client_id"],
            "project_id": response["project_id"],
            "project_slug": response["project_slug"],
            "last_key_id": response["key_id"],
            "last_key_prefix": response["key_prefix"],
            "api_key": response["api_key"],
        }
    )
    local_cfg.pop("onboarding_token", None)
    save_local_config(local_cfg)

    settings = get_mcp_settings()
    print("API key created. This is shown once.")
    print(response["api_key"])
    print("Use this MCP config snippet:")
    snippet = {
        "mcpServers": {
            "eval-mcp": {
                "command": "uvx",
                "args": ["eval-mcp", "serve"],
                "env": {
                    "EVAL_MCP_API_URL": settings.api_url,
                    "EVAL_MCP_API_KEY": response["api_key"],
                },
            }
        }
    }
    print(json.dumps(snippet, indent=2))


async def _cmd_create_project(args: argparse.Namespace) -> None:
    async with api_client() as client:
        response = await client.create_project_for_current_client(
            {
                "name": args.name,
                "slug": args.slug,
                "description": args.description,
            }
        )

    local_cfg = load_local_config()
    local_cfg.update({"project_id": response["id"], "project_slug": response["slug"]})
    save_local_config(local_cfg)

    print("Project created.")
    print(json.dumps(response, indent=2, default=str))
    print(f"Next step: eval-mcp create-api-key --project {response['slug']}")


async def _cmd_whoami() -> None:
    async with api_client() as client:
        response = await client.whoami()
    print(json.dumps(response, indent=2, default=str))


async def _cmd_list_api_keys() -> None:
    async with api_client() as client:
        response = await client.list_api_keys()
    print(json.dumps(response, indent=2, default=str))


async def _cmd_revoke_api_key(key_id: str) -> None:
    async with api_client() as client:
        response = await client.revoke_api_key(key_id)
    print(json.dumps(response, indent=2, default=str))


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "serve":
        run_server(dry_run=args.dry_run)
        return
    if args.command == "api":
        run_api(host=args.host, port=args.port)
        return
    if args.command == "worker":
        run_worker(max_runs=args.max_runs)
        return
    if args.command == "dashboard":
        run_dashboard(host=args.host, port=args.port)
        return
    if args.command == "migrate":
        run_migrations(args.revision)
        return
    if args.command == "register":
        asyncio.run(_cmd_register(args))
        return
    if args.command == "create-api-key":
        asyncio.run(_cmd_create_api_key(args))
        return
    if args.command == "create-project":
        asyncio.run(_cmd_create_project(args))
        return
    if args.command == "whoami":
        asyncio.run(_cmd_whoami())
        return
    if args.command == "list-api-keys":
        asyncio.run(_cmd_list_api_keys())
        return
    if args.command == "revoke-api-key":
        asyncio.run(_cmd_revoke_api_key(args.key_id))
        return

    parser.error(f"Unknown command: {args.command}")
