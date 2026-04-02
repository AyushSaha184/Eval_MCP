from __future__ import annotations

import re
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError, ValidationFailed
from db.repositories.clients import ClientsRepository
from db.repositories.projects import ProjectsRepository
from services.api_keys import hash_secret, verify_secret


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "project"


def _normalize_identifier(identifier: str) -> str:
    value = identifier.strip().lower()
    if not value:
        raise ValidationFailed("Registration identifier is required.")
    return value


class ClientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.clients = ClientsRepository(session)
        self.projects = ProjectsRepository(session)

    async def register(self, *, identifier: str, password: str, display_name: str | None) -> tuple[object, object, str, bool]:
        normalized_identifier = _normalize_identifier(identifier)
        client = await self.clients.get_by_identifier(normalized_identifier)
        password_hash = hash_secret(password)
        onboarding_token = secrets.token_urlsafe(32)
        onboarding_token_hash = hash_secret(onboarding_token)
        created = False
        if client is None:
            client = await self.clients.create(
                account_identifier=normalized_identifier,
                password_hash=password_hash,
                display_name=display_name,
                onboarding_token_hash=onboarding_token_hash,
            )
            created = True
        else:
            if not verify_secret(password, client.password_hash):
                raise ValidationFailed("An account with that identifier already exists. Use eval-mcp login instead.")
            await self.clients.update_onboarding_token_hash(
                client_id=client.id,
                onboarding_token_hash=onboarding_token_hash,
            )
            if display_name and not client.display_name:
                client.display_name = display_name
                await self.session.flush()

        project = await self._get_or_create_default_project(client.id, normalized_identifier)
        return client, project, onboarding_token, created

    async def _get_or_create_default_project(self, client_id: str, identifier: str):
        projects = await self.projects.list_for_client(client_id=client_id, limit=1)
        if projects:
            return projects[0]

        base = _slugify(identifier.split("@", 1)[0])
        candidate = f"{base}-default"
        suffix = 1
        while await self.projects.get_by_identifier(candidate):
            suffix += 1
            candidate = f"{base}-default-{suffix}"

        return await self.projects.create(
            slug=candidate,
            name=f"{base.title()} Default Project",
            description="Default project created during hosted onboarding.",
            created_by=identifier,
            owner_client_id=client_id,
        )

    async def get_required(self, identifier: str):
        normalized_identifier = _normalize_identifier(identifier)
        client = await self.clients.get_by_identifier(normalized_identifier)
        if client is None:
            raise NotFoundError("Client account was not found. Register first.")
        return client

    async def validate_onboarding_token(self, *, identifier: str, onboarding_token: str) -> object:
        client = await self.get_required(identifier)
        if not client.is_active:
            raise ValidationFailed("Client account is inactive.")
        if not verify_secret(onboarding_token, client.onboarding_token_hash):
            raise ValidationFailed("Invalid onboarding token. Run register again.")
        return client

    async def consume_onboarding_token(self, *, client_id: str) -> None:
        await self.clients.clear_onboarding_token_hash(client_id=client_id)

    async def authenticate(self, *, identifier: str, password: str):
        client = await self.get_required(identifier)
        if not client.is_active:
            raise ValidationFailed("Client account is inactive.")
        if not verify_secret(password, client.password_hash):
            raise ValidationFailed("Invalid email or password.")
        return client
