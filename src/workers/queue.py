from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as redis

from core.config import get_settings
from core.errors import QueueError


logger = logging.getLogger(__name__)


class QueueBackend:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def enqueue(self, run_id: str) -> None:
        raise NotImplementedError

    async def dequeue(self) -> str | None:
        raise NotImplementedError


class DatabaseQueue(QueueBackend):
    async def enqueue(self, run_id: str) -> None:
        logger.info("Enqueued run.", extra={"run_id": run_id})

    async def dequeue(self) -> str | None:
        return None


class RedisQueue(QueueBackend):
    def __init__(self) -> None:
        super().__init__()
        if not self.settings.redis_url:
            raise QueueError("REDIS_URL must be set when QUEUE_BACKEND=redis.")
        self.client = redis.from_url(self.settings.redis_url, decode_responses=True)

    async def enqueue(self, run_id: str) -> None:
        await self.client.rpush(self.settings.redis_queue_name, run_id)
        logger.info("Enqueued run in Redis.", extra={"run_id": run_id})

    async def dequeue(self) -> str | None:
        item = await self.client.blpop(self.settings.redis_queue_name, timeout=int(self.settings.worker_poll_interval_seconds))
        if not item:
            return None
        _, run_id = item
        return run_id


def build_queue() -> QueueBackend:
    settings = get_settings()
    if settings.queue_backend == "redis":
        return RedisQueue()
    return DatabaseQueue()
