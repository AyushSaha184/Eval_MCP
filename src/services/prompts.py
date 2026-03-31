from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import ConflictError, NotFoundError
from db.repositories.prompts import PromptsRepository
from domain.schemas import AdHocPrompt, PromptRead, PromptReference, PromptRegistration
from services.projects import ProjectService


def _to_prompt_read(prompt) -> PromptRead:
    return PromptRead(
        id=prompt.id,
        project_id=prompt.project_id,
        prompt_key=prompt.prompt_key,
        version=prompt.version,
        content=prompt.content,
        system_prompt=prompt.system_prompt,
        metadata=prompt.metadata_json,
        created_by=prompt.created_by,
        created_at=prompt.created_at,
    )


class PromptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.prompts = PromptsRepository(session)

    async def register_prompt(self, request: PromptRegistration) -> PromptRead:
        project = await self.projects.get_project_model(request.project)
        version = request.version or (
            await self.prompts.get_latest_version(
                project_id=project.id,
                prompt_key=request.prompt_key,
            )
            + 1
        )
        existing = await self.prompts.get_by_reference(
            project_id=project.id,
            prompt_key=request.prompt_key,
            version=version,
        )
        if existing is not None:
            raise ConflictError(
                f"Prompt `{request.prompt_key}` version `{version}` already exists in project `{project.slug}`."
            )
        prompt = await self.prompts.create(
            project_id=project.id,
            prompt_key=request.prompt_key,
            version=version,
            content=request.content,
            system_prompt=request.system_prompt,
            metadata_json=request.metadata,
            created_by=request.created_by,
        )
        return _to_prompt_read(prompt)

    async def resolve_prompt(self, project_identifier: str, reference: PromptReference):
        project = await self.projects.get_project_model(project_identifier)
        prompt = await self.prompts.get_by_reference(
            project_id=project.id,
            prompt_id=reference.prompt_id,
            prompt_key=reference.prompt_key,
            version=reference.version,
        )
        if prompt is None:
            raise NotFoundError("Prompt reference could not be resolved.")
        return prompt

    async def snapshot_prompt(
        self,
        *,
        project_identifier: str,
        prompt_reference: PromptReference | None,
        ad_hoc_prompt: AdHocPrompt | None,
    ) -> tuple[object | None, dict]:
        if ad_hoc_prompt is not None:
            return None, {
                "source": "adhoc",
                "prompt_key": ad_hoc_prompt.prompt_key or "adhoc_prompt",
                "version": None,
                "content": ad_hoc_prompt.content,
                "system_prompt": ad_hoc_prompt.system_prompt,
                "metadata": ad_hoc_prompt.metadata,
            }

        if prompt_reference is None:
            raise NotFoundError("No prompt input was provided.")
        prompt = await self.resolve_prompt(project_identifier, prompt_reference)
        return prompt, {
            "source": "registry",
            "prompt_id": prompt.id,
            "prompt_key": prompt.prompt_key,
            "version": prompt.version,
            "content": prompt.content,
            "system_prompt": prompt.system_prompt,
            "metadata": prompt.metadata_json,
        }

    async def list_prompts(self, project_identifier: str) -> list[PromptRead]:
        project = await self.projects.get_project_model(project_identifier)
        prompts = await self.prompts.list_by_project(project_id=project.id)
        return [_to_prompt_read(prompt) for prompt in prompts]

