from __future__ import annotations

import asyncio
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from api.app import app as api_app
from dashboard.app import app as dashboard_app
from workers.jobs import run_worker_loop


def run_api(*, host: str, port: int) -> None:
    uvicorn.run(api_app, host=host, port=port)


def run_dashboard(*, host: str, port: int) -> None:
    uvicorn.run(dashboard_app, host=host, port=port)


def run_worker(*, max_runs: int | None = None) -> None:
    asyncio.run(run_worker_loop(max_runs=max_runs))


def run_migrations(revision: str = "head") -> None:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, revision)
