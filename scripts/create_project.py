from __future__ import annotations

import argparse
import asyncio

from db.session import session_scope
from domain.schemas import ProjectCreate
from services.projects import ProjectService


async def _main(args: argparse.Namespace) -> None:
    async with session_scope() as session:
        project = await ProjectService(session).create_project(
            ProjectCreate(
                name=args.name,
                slug=args.slug,
                description=args.description,
                created_by=args.created_by,
            )
        )
        print(project.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an Eval_MCP project.")
    parser.add_argument("name")
    parser.add_argument("--slug")
    parser.add_argument("--description")
    parser.add_argument("--created-by", default="script")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()

