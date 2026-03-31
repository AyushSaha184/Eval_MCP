from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.hashing import hash_dataset_cases
from db.repositories.datasets import DatasetsRepository
from domain.schemas import DatasetCaseInput, DatasetCaseRead, DatasetRead, DatasetReference, DatasetRegistration, RagCaseInput
from services.projects import ProjectService


def _normalize_case(case: DatasetCaseInput) -> dict:
    return {
        "input_text": " ".join(case.input_text.split()),
        "expected_output": case.expected_output,
        "context": [entry.strip() for entry in case.context],
        "labels": sorted({label.strip() for label in case.labels if label.strip()}),
        "metadata": case.metadata,
    }


def _to_dataset_read(dataset, case_count: int) -> DatasetRead:
    return DatasetRead(
        id=dataset.id,
        project_id=dataset.project_id,
        dataset_name=dataset.dataset_name,
        version_hash=dataset.version_hash,
        description=dataset.description,
        tags=dataset.tags_json,
        metadata=dataset.metadata_json,
        case_count=case_count,
        created_by=dataset.created_by,
        created_at=dataset.created_at,
    )


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.datasets = DatasetsRepository(session)

    async def register_dataset(self, request: DatasetRegistration) -> DatasetRead:
        project = await self.projects.get_project_model(request.project)
        normalized_cases = [_normalize_case(case) for case in request.cases]
        version_hash = hash_dataset_cases(
            normalized_cases,
            metadata={
                "description": request.description,
                "tags": sorted(request.tags),
                "metadata": request.metadata,
            },
        )
        existing = await self.datasets.get_by_reference(
            project_id=project.id,
            dataset_name=request.dataset_name,
            version_hash=version_hash,
        )
        if existing is not None:
            case_count = await self.datasets.count_cases(existing.id)
            return _to_dataset_read(existing, case_count)

        dataset = await self.datasets.create(
            project_id=project.id,
            dataset_name=request.dataset_name,
            version_hash=version_hash,
            description=request.description,
            tags_json=sorted(request.tags),
            metadata_json=request.metadata,
            created_by=request.created_by,
        )
        await self.datasets.create_cases(dataset_id=dataset.id, cases=normalized_cases)
        return _to_dataset_read(dataset, len(normalized_cases))

    async def register_inline_rag_dataset(
        self,
        *,
        project_identifier: str,
        dataset_name: str,
        cases: list[RagCaseInput],
        created_by: str | None,
    ) -> DatasetRead:
        request = DatasetRegistration(
            project=project_identifier,
            dataset_name=dataset_name,
            cases=[
                DatasetCaseInput(
                    input_text=case.query,
                    expected_output=case.expected_output,
                    context=case.expected_context,
                    metadata=case.metadata,
                )
                for case in cases
            ],
            created_by=created_by,
        )
        return await self.register_dataset(request)

    async def resolve_dataset(self, project_identifier: str, reference: DatasetReference):
        project = await self.projects.get_project_model(project_identifier)
        dataset = await self.datasets.get_by_reference(
            project_id=project.id,
            dataset_id=reference.dataset_id,
            dataset_name=reference.dataset_name,
            version_hash=reference.version_hash,
        )
        if dataset is None:
            from core.errors import NotFoundError

            raise NotFoundError("Dataset reference could not be resolved.")
        cases = await self.datasets.get_cases(dataset.id)
        return dataset, cases

    async def list_datasets(self, project_identifier: str) -> list[DatasetRead]:
        project = await self.projects.get_project_model(project_identifier)
        datasets = await self.datasets.list_by_project(project_id=project.id)
        response: list[DatasetRead] = []
        for dataset in datasets:
            response.append(_to_dataset_read(dataset, await self.datasets.count_cases(dataset.id)))
        return response

    def snapshot_dataset(self, dataset, case_count: int, selected_case_indices: list[int] | None = None) -> dict:
        return {
            "dataset_id": dataset.id,
            "dataset_name": dataset.dataset_name,
            "version_hash": dataset.version_hash,
            "description": dataset.description,
            "tags": dataset.tags_json,
            "metadata": dataset.metadata_json,
            "case_count": case_count,
            "selected_case_indices": selected_case_indices or [],
        }

    @staticmethod
    def to_case_reads(cases) -> list[DatasetCaseRead]:
        return [
            DatasetCaseRead(
                id=case.id,
                dataset_id=case.dataset_id,
                case_index=case.case_index,
                input_text=case.input_text,
                expected_output=case.expected_output,
                context=case.context_json,
                labels=case.labels_json,
                metadata=case.metadata_json,
            )
            for case in cases
        ]

