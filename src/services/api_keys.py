from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError, UnauthorizedError, ValidationFailed
from db.repositories.api_keys import APIKeysRepository
from db.repositories.projects import ProjectsRepository


_HASH_SCHEME = "pbkdf2_sha256"
_HASH_ITERATIONS = 600_000
_KEY_PREFIX_NAMESPACE = "emcp"


@dataclass
class GeneratedAPIKey:
    raw_key: str
    key_prefix: str
    key_hash: str


def hash_secret(secret_value: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret_value.encode("utf-8"),
        salt.encode("utf-8"),
        _HASH_ITERATIONS,
    )
    return f"{_HASH_SCHEME}${_HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_secret(secret_value: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, iterations_raw, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        # Backward compatibility for early onboarding tokens stored in plain text.
        return hmac.compare_digest(secret_value, stored_hash)
    if scheme != _HASH_SCHEME:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret_value.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations_raw),
    )
    return hmac.compare_digest(digest.hex(), expected)


def parse_key_prefix(raw_key: str) -> str | None:
    if not raw_key.startswith(f"{_KEY_PREFIX_NAMESPACE}_"):
        return None
    parts = raw_key.split("_", 2)
    if len(parts) != 3:
        return None
    prefix = f"{_KEY_PREFIX_NAMESPACE}_{parts[1]}"
    return prefix


def generate_api_key() -> GeneratedAPIKey:
    human_prefix = secrets.token_hex(4)
    key_prefix = f"{_KEY_PREFIX_NAMESPACE}_{human_prefix}"
    secret = secrets.token_urlsafe(32)
    raw_key = f"{key_prefix}_{secret}"
    return GeneratedAPIKey(raw_key=raw_key, key_prefix=key_prefix, key_hash=hash_secret(raw_key))


class APIKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.api_keys = APIKeysRepository(session)
        self.projects = ProjectsRepository(session)

    async def create_for_client(
        self,
        *,
        client_id: str,
        label: str | None,
        project_identifier: str | None,
    ) -> tuple[object, GeneratedAPIKey]:
        project = await self._resolve_project(client_id=client_id, project_identifier=project_identifier)
        generated = generate_api_key()
        row = await self.api_keys.create(
            client_id=client_id,
            project_id=project.id,
            label=(label or "default").strip() or "default",
            key_prefix=generated.key_prefix,
            key_hash=generated.key_hash,
        )
        return row, generated

    async def list_for_client(self, client_id: str) -> list[object]:
        return await self.api_keys.list_for_client(client_id)

    async def revoke_for_client(self, *, client_id: str, key_id: str) -> None:
        row = await self.api_keys.get_by_id(key_id)
        if row is None or row.client_id != client_id:
            raise NotFoundError("API key was not found.")
        await self.api_keys.revoke(key_id, datetime.now(timezone.utc))

    async def touch_last_used(self, key_id: str) -> None:
        await self.api_keys.touch_last_used(key_id, datetime.now(timezone.utc))

    async def _resolve_project(self, *, client_id: str, project_identifier: str | None):
        if project_identifier:
            project = await self.projects.get_by_identifier(project_identifier)
            if project is None or project.owner_client_id != client_id:
                raise UnauthorizedError("API key scope cannot target an inaccessible project.")
            return project

        projects = await self.projects.list_for_client(client_id=client_id, limit=1)
        if not projects:
            raise ValidationFailed("Client does not have a project scope.")
        return projects[0]
