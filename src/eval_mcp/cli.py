from __future__ import annotations

import argparse
from collections.abc import Sequence

from core.config import get_settings
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

    return parser


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

    parser.error(f"Unknown command: {args.command}")
