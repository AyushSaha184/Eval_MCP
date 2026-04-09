from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.hashing import build_cache_key, hash_prompt_snapshot
from core.metrics_registry import get_metric_definition
from db.models import EvalRun
from db.repositories.runs import RunsRepository
from domain.enums import RunType


class CachingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = RunsRepository(session)

    @staticmethod
    def sanitize_runtime_config(runtime_config: dict) -> dict:
        return {
            key: value
            for key, value in runtime_config.items()
            if key not in {"labels"} and value not in (None, [], {})
        }

    def build_run_cache_key(
        self,
        *,
        project_id: str,
        run_type: str,
        prompt_snapshot: dict,
        dataset_snapshot: dict,
        metrics: list[str],
        model_config: dict,
        retriever_config: dict | None,
        runtime_config: dict,
    ) -> str:
        backend_fingerprint = {}
        for metric in sorted(metrics):
            metric_def = get_metric_definition(metric)
            backend_fingerprint[metric] = {
                "provider": metric_def.provider,
                "family": metric_def.family,
            }
        payload = {
            "project_id": project_id,
            "run_type": run_type,
            "prompt_snapshot_hash": hash_prompt_snapshot(prompt_snapshot),
            "dataset_version_hash": dataset_snapshot.get("version_hash"),
            "selected_case_indices": dataset_snapshot.get("selected_case_indices", []),
            "metrics": sorted(metrics),
            "model_config": model_config,
            "retriever_config": retriever_config or {},
            "runtime_config": self.sanitize_runtime_config(runtime_config),
            "backend_fingerprint": backend_fingerprint,
        }
        return build_cache_key(payload)

    async def find_cached_run(
        self, *, project_id: str, cache_key: str, run_type: RunType
    ) -> EvalRun | None:
        return await self.runs.find_cached_completed(
            project_id=project_id,
            cache_key=cache_key,
            run_type=run_type,
        )

    async def find_inflight_run(
        self, *, project_id: str, cache_key: str, run_type: RunType
    ) -> EvalRun | None:
        return await self.runs.find_cached_inflight(
            project_id=project_id,
            cache_key=cache_key,
            run_type=run_type,
        )
