from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClientApiKey


class APIKeysRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        client_id: str,
        project_id: str,
        label: str,
        key_prefix: str,
        key_hash: str,
    ) -> ClientApiKey:
        row = ClientApiKey(
            client_id=client_id,
            project_id=project_id,
            label=label,
            key_prefix=key_prefix,
            key_hash=key_hash,
            is_active=True,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def list_active_by_prefix(self, key_prefix: str) -> list[ClientApiKey]:
        stmt = select(ClientApiKey).where(
            ClientApiKey.key_prefix == key_prefix,
            ClientApiKey.is_active.is_(True),
            ClientApiKey.revoked_at.is_(None),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_client(self, client_id: str) -> list[ClientApiKey]:
        stmt = (
            select(ClientApiKey)
            .where(ClientApiKey.client_id == client_id)
            .order_by(ClientApiKey.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_id(self, key_id: str) -> ClientApiKey | None:
        return await self.session.get(ClientApiKey, key_id)

    async def touch_last_used(self, key_id: str, when: datetime) -> None:
        row = await self.get_by_id(key_id)
        if row is None:
            return
        row.last_used_at = when
        await self.session.flush()

    async def revoke(self, key_id: str, when: datetime) -> None:
        row = await self.get_by_id(key_id)
        if row is None:
            return
        row.is_active = False
        row.revoked_at = when
        await self.session.flush()
