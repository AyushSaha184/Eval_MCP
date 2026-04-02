from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import require_api_key
from core.errors import UnauthorizedError
from db.session import session_scope
from domain.schemas import (
    ApiKeyListItem,
    CreateApiKeyRequest,
    CreateScopedApiKeyRequest,
    HostedProjectCreateRequest,
    LoginClientRequest,
    ProjectCreate,
    RegisterClientRequest,
    WhoAmIResponse,
)
from services.api_keys import APIKeyService
from services.auth import AuthContext
from services.clients import ClientService
from services.projects import ProjectService
from db.repositories.clients import ClientsRepository
from db.repositories.projects import ProjectsRepository


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register")
async def register_client(request: RegisterClientRequest) -> dict:
    async with session_scope() as session:
        client, project, onboarding_token, created = await ClientService(session).register(
            identifier=request.identifier,
            password=request.password,
            display_name=request.display_name,
        )
        return {
            "ok": True,
            "client_id": client.id,
            "identifier": client.account_identifier,
            "display_name": client.display_name,
            "project_id": project.id,
            "project_slug": project.slug,
            "onboarding_token": onboarding_token,
            "created": created,
        }


@router.post("/login")
async def login_client(request: LoginClientRequest) -> dict:
    async with session_scope() as session:
        clients = ClientService(session)
        client = await clients.authenticate(identifier=request.identifier, password=request.password)
        key_row, generated = await APIKeyService(session).create_for_client(
            client_id=client.id,
            label=request.label,
            project_identifier=request.project,
        )
        project = await ProjectsRepository(session).get_by_id(key_row.project_id)
        return {
            "ok": True,
            "key_id": key_row.id,
            "key_prefix": key_row.key_prefix,
            "api_key": generated.raw_key,
            "client_id": client.id,
            "identifier": client.account_identifier,
            "project_id": project.id,
            "project_slug": project.slug,
            "label": key_row.label,
        }


@router.post("/api-keys")
async def create_api_key(request: CreateApiKeyRequest) -> dict:
    async with session_scope() as session:
        clients = ClientService(session)
        client = await clients.validate_onboarding_token(
            identifier=request.identifier,
            onboarding_token=request.onboarding_token,
        )
        key_row, generated = await APIKeyService(session).create_for_client(
            client_id=client.id,
            label=request.label,
            project_identifier=request.project,
        )
        await clients.consume_onboarding_token(client_id=client.id)
        project = await ProjectsRepository(session).get_by_id(key_row.project_id)
        return {
            "ok": True,
            "key_id": key_row.id,
            "key_prefix": key_row.key_prefix,
            "api_key": generated.raw_key,
            "client_id": client.id,
            "identifier": client.account_identifier,
            "project_id": project.id,
            "project_slug": project.slug,
            "label": key_row.label,
        }


@router.post("/api-keys/current")
async def create_api_key_for_current_client(
    request: CreateScopedApiKeyRequest,
    auth: AuthContext = Depends(require_api_key),
) -> dict:
    if auth.is_legacy_admin:
        raise UnauthorizedError("Legacy keys cannot create DB-backed API keys.")
    async with session_scope() as session:
        key_row, generated = await APIKeyService(session).create_for_client(
            client_id=auth.client_id,
            label=getattr(request, "label", None),
            project_identifier=getattr(request, "project", None),
        )
        client = await ClientsRepository(session).get_by_id(auth.client_id)
        project = await ProjectsRepository(session).get_by_id(key_row.project_id)
        return {
            "ok": True,
            "key_id": key_row.id,
            "key_prefix": key_row.key_prefix,
            "api_key": generated.raw_key,
            "client_id": client.id if client else auth.client_id,
            "identifier": client.account_identifier if client else None,
            "project_id": project.id,
            "project_slug": project.slug,
            "label": key_row.label,
        }


@router.post("/projects")
async def create_hosted_project(
    request: HostedProjectCreateRequest,
    auth: AuthContext = Depends(require_api_key),
) -> dict:
    if auth.is_legacy_admin:
        raise UnauthorizedError("Legacy keys cannot create hosted projects.")
    async with session_scope() as session:
        client = await ClientsRepository(session).get_by_id(auth.client_id)
        if client is None or not client.is_active:
            raise UnauthorizedError("Client account is inactive.")
        project = await ProjectService(session).create_project(
            ProjectCreate(
                name=request.name,
                slug=request.slug,
                description=request.description,
                created_by=client.account_identifier,
            ),
            owner_client_id=client.id,
        )
        return {"ok": True, **project.model_dump(mode="json")}


@router.get("/whoami")
async def whoami(auth: AuthContext = Depends(require_api_key)) -> dict:
    async with session_scope() as session:
        if auth.is_legacy_admin:
            return {
                "ok": True,
                **WhoAmIResponse(mode="legacy-admin").model_dump(mode="json"),
            }

        client = await ClientsRepository(session).get_by_id(auth.client_id)
        project = await ProjectsRepository(session).get_by_id(auth.project_id)
        key_rows = await APIKeyService(session).list_for_client(auth.client_id)
        key_row = next((item for item in key_rows if item.id == auth.api_key_id), None)
        return {
            "ok": True,
            **WhoAmIResponse(
                mode=auth.mode,
                client_id=client.id if client else None,
                identifier=client.account_identifier if client else None,
                project_id=project.id if project else None,
                project_slug=project.slug if project else None,
                key_id=key_row.id if key_row else auth.api_key_id,
                key_prefix=key_row.key_prefix if key_row else None,
            ).model_dump(mode="json"),
        }


@router.get("/api-keys")
async def list_api_keys(auth: AuthContext = Depends(require_api_key)) -> dict:
    if auth.is_legacy_admin:
        raise UnauthorizedError("Legacy keys cannot list DB API keys.")
    async with session_scope() as session:
        rows = await APIKeyService(session).list_for_client(auth.client_id)
        return {
            "ok": True,
            "items": [
                ApiKeyListItem(
                    id=row.id,
                    label=row.label,
                    key_prefix=row.key_prefix,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    last_used_at=row.last_used_at,
                    revoked_at=row.revoked_at,
                ).model_dump(mode="json")
                for row in rows
            ],
        }


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(key_id: str, auth: AuthContext = Depends(require_api_key)) -> dict:
    if auth.is_legacy_admin:
        raise UnauthorizedError("Legacy keys cannot revoke DB API keys.")
    async with session_scope() as session:
        await APIKeyService(session).revoke_for_client(client_id=auth.client_id, key_id=key_id)
        return {"ok": True, "key_id": key_id, "revoked": True}
