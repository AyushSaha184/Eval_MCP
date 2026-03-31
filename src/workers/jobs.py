from __future__ import annotations

import asyncio
import logging

from core.config import get_settings
from db.repositories.runs import RunsRepository
from db.session import session_scope
from workers.dispatcher import RunDispatcher
from workers.queue import build_queue
from workers.retry import run_with_retry


logger = logging.getLogger(__name__)


async def process_run(run_public_id: str) -> None:
    settings = get_settings()

    async def _process() -> None:
        async with session_scope(settings) as session:
            runs_repo = RunsRepository(session)
            run = await runs_repo.get_by_public_id(run_public_id)
            if run is None:
                return
            if run.status != "running":
                await runs_repo.mark_running(run.id, attempt_count=run.attempt_count + 1)
            await RunDispatcher(session).dispatch(run)

    try:
        await run_with_retry(_process, max_attempts=settings.worker_max_retries)
    except Exception as exc:
        async with session_scope(settings) as session:
            runs_repo = RunsRepository(session)
            run = await runs_repo.get_by_public_id(run_public_id)
            if run is not None:
                await runs_repo.finalize_failure(
                    run_db_id=run.id,
                    error_message=str(exc),
                    processed_cases=run.processed_cases,
                )
        logger.exception("Run execution failed.", extra={"run_id": run_public_id})


async def process_next_queued_run() -> str | None:
    settings = get_settings()
    queue = build_queue()
    if settings.queue_backend == "redis":
        run_id = await queue.dequeue()
        if run_id is None:
            return None
        async with session_scope(settings) as session:
            claimed = await RunsRepository(session).claim_queued_run_by_public_id(run_id)
            if claimed is None:
                return None
        await process_run(run_id)
        return run_id

    async with session_scope(settings) as session:
        run = await RunsRepository(session).claim_next_queued_run()
        if run is None:
            return None
        run_id = run.run_id
    await queue.enqueue(run_id)
    await process_run(run_id)
    return run_id


async def run_worker_loop(*, max_runs: int | None = None) -> None:
    settings = get_settings()
    processed = 0
    while max_runs is None or processed < max_runs:
        run_id = await process_next_queued_run()
        if run_id is None:
            await asyncio.sleep(settings.worker_poll_interval_seconds)
            continue
        processed += 1


def main() -> None:
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
