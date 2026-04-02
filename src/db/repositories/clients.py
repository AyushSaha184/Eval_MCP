from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Client


class ClientsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, client_id: str) -> Client | None:
        return await self.session.get(Client, client_id)

    async def get_by_identifier(self, identifier: str) -> Client | None:
        stmt = select(Client).where(Client.account_identifier == identifier)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        account_identifier: str,
        password_hash: str,
        display_name: str | None,
        onboarding_token_hash: str | None,
    ) -> Client:
        client = Client(
            account_identifier=account_identifier,
            password_hash=password_hash,
            display_name=display_name,
            onboarding_token_hash=onboarding_token_hash,
            is_active=True,
        )
        self.session.add(client)
        await self.session.flush()
        await self.session.refresh(client)
        return client

    async def update_onboarding_token_hash(self, *, client_id: str, onboarding_token_hash: str | None) -> None:
        client = await self.get_by_id(client_id)
        if client is None:
            return
        client.onboarding_token_hash = onboarding_token_hash
        await self.session.flush()

    async def clear_onboarding_token_hash(self, *, client_id: str) -> None:
        await self.update_onboarding_token_hash(client_id=client_id, onboarding_token_hash=None)

    async def update_password_hash(self, *, client_id: str, password_hash: str) -> None:
        client = await self.get_by_id(client_id)
        if client is None:
            return
        client.password_hash = password_hash
        await self.session.flush()
