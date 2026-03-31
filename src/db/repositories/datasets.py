from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Dataset, DatasetCase


class DatasetsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        project_id: str,
        dataset_name: str,
        version_hash: str,
        description: str | None,
        tags_json: list[str],
        metadata_json: dict,
        created_by: str | None,
    ) -> Dataset:
        dataset = Dataset(
            project_id=project_id,
            dataset_name=dataset_name,
            version_hash=version_hash,
            description=description,
            tags_json=tags_json,
            metadata_json=metadata_json,
            created_by=created_by,
        )
        self.session.add(dataset)
        await self.session.flush()
        await self.session.refresh(dataset)
        return dataset

    async def create_cases(
        self,
        *,
        dataset_id: str,
        cases: list[dict],
    ) -> list[DatasetCase]:
        rows = [
            DatasetCase(
                dataset_id=dataset_id,
                case_index=index,
                input_text=case["input_text"],
                expected_output=case.get("expected_output"),
                context_json=case.get("context", []),
                labels_json=case.get("labels", []),
                metadata_json=case.get("metadata", {}),
            )
            for index, case in enumerate(cases)
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def count_cases(self, dataset_id: str) -> int:
        stmt = select(func.count(DatasetCase.id)).where(DatasetCase.dataset_id == dataset_id)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def get_by_reference(
        self,
        *,
        project_id: str,
        dataset_id: str | None = None,
        dataset_name: str | None = None,
        version_hash: str | None = None,
    ) -> Dataset | None:
        if dataset_id:
            stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.project_id == project_id)
            return (await self.session.execute(stmt)).scalar_one_or_none()

        if not dataset_name:
            return None

        stmt = select(Dataset).where(
            Dataset.project_id == project_id,
            Dataset.dataset_name == dataset_name,
        )
        if version_hash is not None:
            stmt = stmt.where(Dataset.version_hash == version_hash)
        else:
            stmt = stmt.order_by(desc(Dataset.created_at)).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_by_project(self, *, project_id: str) -> list[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .order_by(Dataset.dataset_name.asc(), Dataset.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_cases(self, dataset_id: str) -> list[DatasetCase]:
        stmt = (
            select(DatasetCase)
            .where(DatasetCase.dataset_id == dataset_id)
            .order_by(DatasetCase.case_index.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

