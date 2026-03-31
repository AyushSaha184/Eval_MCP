from __future__ import annotations

import asyncio

from db.session import session_scope
from domain.schemas import DatasetCaseInput, DatasetRegistration, ProjectCreate, PromptRegistration
from services.datasets import DatasetService
from services.projects import ProjectService
from services.prompts import PromptService


async def main() -> None:
    async with session_scope() as session:
        projects = ProjectService(session)
        prompts = PromptService(session)
        datasets = DatasetService(session)

        project = await projects.create_project(
            ProjectCreate(
                name="Demo Eval Project",
                slug="demo-eval",
                description="Seeded project for local demos.",
                created_by="seed-script",
            )
        )
        await prompts.register_prompt(
            PromptRegistration(
                project=project.slug,
                prompt_key="qa",
                version=1,
                content="good prompt",
                created_by="seed-script",
            )
        )
        dataset = await datasets.register_dataset(
            DatasetRegistration(
                project=project.slug,
                dataset_name="demo_dataset",
                created_by="seed-script",
                cases=[
                    DatasetCaseInput(
                        input_text="What is the capital of France?",
                        expected_output="Paris",
                        context=["France has capital Paris."],
                    ),
                    DatasetCaseInput(
                        input_text="What is 5 + 7?",
                        expected_output="12",
                        context=["Arithmetic basics."],
                    ),
                ],
            )
        )
        print(project.model_dump_json(indent=2))
        print(dataset.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

