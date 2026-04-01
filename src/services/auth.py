from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.errors import NotFoundError, UnauthorizedError
from db.repositories.api_keys import APIKeysRepository
from db.repositories.clients import ClientsRepository
from db.repositories.projects import ProjectsRepository
from db.repositories.runs import RunsRepository
from services.api_keys import parse_key_prefix, verify_secret


@dataclass
class AuthContext:
    mode: str
    client_id: str | None = None
    project_id: str | None = None
    api_key_id: str | None = None

    @property
    def is_legacy_admin(self) -> bool:
        return self.mode == "legacy-admin"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.api_keys = APIKeysRepository(session)
        self.clients = ClientsRepository(session)
        self.projects = ProjectsRepository(session)
        self.runs = RunsRepository(session)

    async def resolve_api_key_context(self, provided_key: str) -> AuthContext | None:
        prefix = parse_key_prefix(provided_key)
        if prefix:
            key_rows = await self.api_keys.list_active_by_prefix(prefix)
            for key_row in key_rows:
                if not verify_secret(provided_key, key_row.key_hash):
                    continue
                client = await self.clients.get_by_id(key_row.client_id)
                if client is None or not client.is_active:
                    continue
                project = await self.projects.get_by_id(key_row.project_id)
                if project is None:
                    continue
                await self.api_keys.touch_last_used(key_row.id, datetime.now(timezone.utc))
                return AuthContext(
                    mode="db-key",
                    client_id=client.id,
                    project_id=project.id,
                    api_key_id=key_row.id,
                )

        for expected in get_settings().valid_api_keys:
            if hmac.compare_digest(provided_key, expected):
                return AuthContext(mode="legacy-admin")
        return None

    async def authorize_project(self, auth: AuthContext, project_identifier: str):
        project = await self.projects.get_by_identifier(project_identifier)
        if project is None:
            raise NotFoundError(f"Project `{project_identifier}` was not found.")
        if auth.is_legacy_admin:
            return project
        if project.id != auth.project_id:
            raise UnauthorizedError("Project access is not allowed for this API key.")
        return project

    async def authorize_run(self, auth: AuthContext, run_id: str):
        run = await self.runs.get_by_public_id(run_id)
        if run is None:
            raise NotFoundError(f"Run `{run_id}` was not found.")
        if auth.is_legacy_admin:
            return run
        if run.project_id != auth.project_id:
            raise UnauthorizedError("Run access is not allowed for this API key.")
        return run
