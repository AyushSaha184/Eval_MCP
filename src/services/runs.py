from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError, ValidationFailed
from core.ids import generate_run_id
from db.repositories.annotations import AnnotationsRepository
from db.repositories.runs import RunsRepository
from domain.enums import RunStatus, RunType, TriggerSource
from domain.schemas import (
    AdHocPrompt,
    AnnotationRead,
    AnnotationRequest,
    DatasetReference,
    ModelConfig,
    RagScoreRequest,
    RetrieverConfig,
    RerunFailedRequest,
    RunEvalRequest,
    RunQueued,
    RuntimeConfig,
    SuggestFixRequest,
)
from services.caching import CachingService
from services.datasets import DatasetService
from services.projects import ProjectService
from services.prompts import PromptService
from workers.queue import build_queue


class RunService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.prompts = PromptService(session)
        self.datasets = DatasetService(session)
        self.caching = CachingService(session)
        self.runs = RunsRepository(session)
        self.annotations = AnnotationsRepository(session)
        self.queue = build_queue()

    @staticmethod
    def _resolve_selected_case_indices(cases, runtime_config: RuntimeConfig) -> list[int]:
        if runtime_config.selected_case_indices:
            valid = {case.case_index for case in cases}
            selected = sorted(index for index in runtime_config.selected_case_indices if index in valid)
            if not selected:
                raise ValidationFailed("Selected case indices did not match the dataset.")
            return selected
        if runtime_config.case_limit:
            return [case.case_index for case in cases[: runtime_config.case_limit]]
        return []

    async def run_eval_suite(
        self,
        request: RunEvalRequest,
        *,
        run_type: RunType = RunType.PROMPT_EVAL,
    ) -> RunQueued:
        project = await self.projects.get_project_model(request.project)
        prompt_ref, prompt_snapshot = await self.prompts.snapshot_prompt(
            project_identifier=project.id,
            prompt_reference=request.prompt_reference,
            ad_hoc_prompt=request.ad_hoc_prompt,
        )
        dataset, cases = await self.datasets.resolve_dataset(project.id, request.dataset_reference)
        selected_case_indices = self._resolve_selected_case_indices(cases, request.runtime_config)
        dataset_snapshot = self.datasets.snapshot_dataset(
            dataset,
            len(cases),
            selected_case_indices=selected_case_indices,
        )
        runtime_snapshot = request.runtime_config.model_dump(mode="json", exclude_none=True)
        model_snapshot = request.model_settings.model_dump(mode="json", exclude_none=True)
        cache_key = self.caching.build_run_cache_key(
            project_id=project.id,
            run_type=run_type,
            prompt_snapshot=prompt_snapshot,
            dataset_snapshot=dataset_snapshot,
            metrics=request.metrics,
            model_config=model_snapshot,
            retriever_config=None,
            runtime_config=runtime_snapshot,
        )
        if not request.force_rerun:
            inflight = await self.caching.find_inflight_run(
                project_id=project.id,
                cache_key=cache_key,
                run_type=run_type,
            )
            if inflight is not None:
                return RunQueued(
                    run_id=inflight.run_id,
                    status=inflight.status,
                    cached=False,
                    cache_key=cache_key,
                    source_run_id=inflight.run_id,
                )
            cached = await self.caching.find_cached_run(
                project_id=project.id,
                cache_key=cache_key,
                run_type=run_type,
            )
            if cached is not None:
                return RunQueued(
                    run_id=cached.run_id,
                    status=cached.status,
                    cached=True,
                    cache_key=cache_key,
                    source_run_id=cached.run_id,
                )

        baseline_db_id = None
        if request.baseline_run_id:
            baseline = await self.runs.get_by_public_id(request.baseline_run_id)
            if baseline is None:
                raise NotFoundError(f"Baseline run `{request.baseline_run_id}` was not found.")
            baseline_db_id = baseline.id

        effective_case_count = len(selected_case_indices) if selected_case_indices else len(cases)
        run = await self.runs.create(
            run_id=generate_run_id(),
            project_id=project.id,
            run_type=run_type,
            status=RunStatus.QUEUED,
            trigger_source=request.trigger_source,
            triggered_by=request.triggered_by,
            prompt_ref_id=getattr(prompt_ref, "id", None),
            dataset_ref_id=dataset.id,
            baseline_run_id=baseline_db_id,
            metrics_requested_json=request.metrics,
            cache_key=cache_key,
            is_cached_result=False,
            total_cases=effective_case_count,
        )
        await self.runs.create_snapshot(
            run_db_id=run.id,
            prompt_snapshot_json=prompt_snapshot,
            dataset_snapshot_json=dataset_snapshot,
            model_config_snapshot_json=model_snapshot,
            retriever_config_snapshot_json={},
            runtime_config_snapshot_json=runtime_snapshot,
        )
        await self.queue.enqueue(run.run_id)
        return RunQueued(run_id=run.run_id, status=run.status, cached=False, cache_key=cache_key)

    async def score_rag_pipeline(self, request: RagScoreRequest) -> RunQueued:
        dataset_reference = request.dataset_reference
        if dataset_reference is None:
            dataset = await self.datasets.register_inline_rag_dataset(
                project_identifier=request.project,
                dataset_name=request.dataset_name or "rag_inline_dataset",
                cases=request.cases,
                created_by=request.triggered_by,
            )
            dataset_reference = DatasetReference(
                dataset_name=dataset.dataset_name,
                version_hash=dataset.version_hash,
            )

        project = await self.projects.get_project_model(request.project)
        prompt_ref, prompt_snapshot = await self.prompts.snapshot_prompt(
            project_identifier=project.id,
            prompt_reference=request.prompt_reference,
            ad_hoc_prompt=request.ad_hoc_prompt,
        )
        dataset, cases = await self.datasets.resolve_dataset(project.id, dataset_reference)
        selected_case_indices = self._resolve_selected_case_indices(cases, request.runtime_config)
        dataset_snapshot = self.datasets.snapshot_dataset(
            dataset,
            len(cases),
            selected_case_indices=selected_case_indices,
        )
        model_snapshot = request.model_settings.model_dump(mode="json", exclude_none=True)
        retriever_snapshot = request.retriever_config.model_dump(mode="json", exclude_none=True)
        runtime_snapshot = request.runtime_config.model_dump(mode="json", exclude_none=True)
        cache_key = self.caching.build_run_cache_key(
            project_id=project.id,
            run_type=RunType.RAG_EVAL,
            prompt_snapshot=prompt_snapshot,
            dataset_snapshot=dataset_snapshot,
            metrics=request.metrics,
            model_config=model_snapshot,
            retriever_config=retriever_snapshot,
            runtime_config=runtime_snapshot,
        )
        if not request.force_rerun:
            inflight = await self.caching.find_inflight_run(
                project_id=project.id,
                cache_key=cache_key,
                run_type=RunType.RAG_EVAL,
            )
            if inflight is not None:
                return RunQueued(
                    run_id=inflight.run_id,
                    status=inflight.status,
                    cached=False,
                    cache_key=cache_key,
                    source_run_id=inflight.run_id,
                )
            cached = await self.caching.find_cached_run(
                project_id=project.id,
                cache_key=cache_key,
                run_type=RunType.RAG_EVAL,
            )
            if cached is not None:
                return RunQueued(
                    run_id=cached.run_id,
                    status=cached.status,
                    cached=True,
                    cache_key=cache_key,
                    source_run_id=cached.run_id,
                )

        effective_case_count = len(selected_case_indices) if selected_case_indices else len(cases)
        run = await self.runs.create(
            run_id=generate_run_id(),
            project_id=project.id,
            run_type=RunType.RAG_EVAL,
            status=RunStatus.QUEUED,
            trigger_source=request.trigger_source,
            triggered_by=request.triggered_by,
            prompt_ref_id=getattr(prompt_ref, "id", None),
            dataset_ref_id=dataset.id,
            baseline_run_id=None,
            metrics_requested_json=request.metrics,
            cache_key=cache_key,
            is_cached_result=False,
            total_cases=effective_case_count,
        )
        await self.runs.create_snapshot(
            run_db_id=run.id,
            prompt_snapshot_json=prompt_snapshot,
            dataset_snapshot_json=dataset_snapshot,
            model_config_snapshot_json=model_snapshot,
            retriever_config_snapshot_json=retriever_snapshot,
            runtime_config_snapshot_json=runtime_snapshot,
        )
        await self.queue.enqueue(run.run_id)
        return RunQueued(run_id=run.run_id, status=run.status, cached=False, cache_key=cache_key)

    async def queue_suggestion(self, request: SuggestFixRequest) -> RunQueued:
        """Queue a suggestion evaluation run.
        
        This creates a background job to analyze a run for failure patterns
        and generate improvement suggestions via LLM judge. Returns immediately
        with a run_id for polling instead of blocking on LLM evaluation.
        """
        # Get and validate the run being analyzed
        referenced_run = await self.runs.get_by_public_id(request.run_id)
        if referenced_run is None:
            raise NotFoundError(f"Run `{request.run_id}` was not found.")
        
        # Normalize model name once so cache key and snapshot stay consistent.
        resolved_model_name = request.model_name or "gemini-2.5-flash"
        cache_key = f"suggestion_{request.run_id}_{request.case_limit}_{request.cluster_limit}_{resolved_model_name}"

        inflight = await self.caching.find_inflight_run(
            project_id=referenced_run.project_id,
            cache_key=cache_key,
            run_type=RunType.SUGGESTION_EVAL,
        )
        if inflight is not None:
            return RunQueued(
                run_id=inflight.run_id,
                status=inflight.status,
                cached=False,
                cache_key=cache_key,
                source_run_id=inflight.run_id,
            )
        
        # Create a suggestion eval run with request parameters stored in snapshot
        suggestion_run = await self.runs.create(
            run_id=generate_run_id(),
            project_id=referenced_run.project_id,
            run_type=RunType.SUGGESTION_EVAL,
            status=RunStatus.QUEUED,
            trigger_source=TriggerSource.API,
            triggered_by="suggestion_service",
            prompt_ref_id=None,
            dataset_ref_id=None,
            baseline_run_id=None,
            metrics_requested_json=[],
            cache_key=cache_key,
            is_cached_result=False,
            total_cases=1,
        )
        
        # Store suggestion configuration in snapshot's runtime_config_snapshot_json
        # This is where the SuggestionEvalExecutor will read the parameters from
        await self.runs.create_snapshot(
            run_db_id=suggestion_run.id,
            prompt_snapshot_json={},
            dataset_snapshot_json={},
            model_config_snapshot_json={},
            retriever_config_snapshot_json={},
            runtime_config_snapshot_json={
                "referenced_run_id": request.run_id,
                "case_limit": request.case_limit,
                "cluster_limit": request.cluster_limit,
                "model_name": resolved_model_name,
            },
        )
        
        await self.queue.enqueue(suggestion_run.run_id)
        return RunQueued(run_id=suggestion_run.run_id, status=suggestion_run.status, cached=False, cache_key=cache_key)

    async def rerun_failed_cases(self, request: RerunFailedRequest) -> RunQueued:
        source_run = await self.runs.get_by_public_id(request.run_id)
        if source_run is None:
            raise NotFoundError(f"Run `{request.run_id}` was not found.")
        failed_case_indices = await self.runs.get_failed_case_indices(source_run.id)
        if not failed_case_indices:
            raise ValidationFailed("Source run does not have failed cases to rerun.")
        snapshot = await self.runs.get_snapshot(source_run.id)
        prompt_snapshot = snapshot.prompt_snapshot_json
        runtime_data = dict(snapshot.runtime_config_snapshot_json)
        runtime_data["selected_case_indices"] = failed_case_indices
        runtime_config = RuntimeConfig(**runtime_data)

        if source_run.run_type == RunType.RAG_EVAL:
            request_model = RagScoreRequest(
                project=source_run.project_id,
                dataset_reference=DatasetReference(
                    dataset_id=snapshot.dataset_snapshot_json.get("dataset_id"),
                    dataset_name=snapshot.dataset_snapshot_json.get("dataset_name"),
                    version_hash=snapshot.dataset_snapshot_json.get("version_hash"),
                ),
                ad_hoc_prompt=AdHocPrompt(
                    prompt_key=prompt_snapshot.get("prompt_key"),
                    content=prompt_snapshot.get("content", ""),
                    system_prompt=prompt_snapshot.get("system_prompt"),
                    metadata=prompt_snapshot.get("metadata", {}),
                ),
                retriever_config=RetrieverConfig(**snapshot.retriever_config_snapshot_json),
                metrics=source_run.metrics_requested_json,
                model_config=ModelConfig(**snapshot.model_config_snapshot_json),
                runtime_config=runtime_config,
                triggered_by=request.triggered_by,
                force_rerun=request.force_rerun,
            )
            return await self.score_rag_pipeline(request_model)

        request_model = RunEvalRequest(
            project=source_run.project_id,
            dataset_reference=DatasetReference(
                dataset_id=snapshot.dataset_snapshot_json.get("dataset_id"),
                dataset_name=snapshot.dataset_snapshot_json.get("dataset_name"),
                version_hash=snapshot.dataset_snapshot_json.get("version_hash"),
            ),
            ad_hoc_prompt=AdHocPrompt(
                prompt_key=prompt_snapshot.get("prompt_key"),
                content=prompt_snapshot.get("content", ""),
                system_prompt=prompt_snapshot.get("system_prompt"),
                metadata=prompt_snapshot.get("metadata", {}),
            ),
            metrics=source_run.metrics_requested_json,
            model_config=ModelConfig(**snapshot.model_config_snapshot_json),
            runtime_config=runtime_config,
            triggered_by=request.triggered_by,
            force_rerun=request.force_rerun,
        )
        return await self.run_eval_suite(request_model, run_type=source_run.run_type)

    async def annotate_run(self, request: AnnotationRequest) -> AnnotationRead:
        run = await self.runs.get_by_public_id(request.run_id)
        if run is None:
            raise NotFoundError(f"Run `{request.run_id}` was not found.")
        annotation = await self.annotations.create(
            run_id=run.id,
            label=request.label,
            note=request.note,
            created_by=request.created_by,
        )
        return AnnotationRead(
            id=annotation.id,
            run_id=run.run_id,
            label=annotation.label,
            note=annotation.note,
            created_by=annotation.created_by,
            created_at=annotation.created_at,
        )
