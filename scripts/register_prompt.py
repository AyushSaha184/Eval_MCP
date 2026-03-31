from __future__ import annotations

import argparse
import asyncio

from db.session import session_scope
from domain.schemas import PromptRegistration
from services.prompts import PromptService


async def _main(args: argparse.Namespace) -> None:
    async with session_scope() as session:
        prompt = await PromptService(session).register_prompt(
            PromptRegistration(
                project=args.project,
                prompt_key=args.prompt_key,
                version=args.version,
                content=args.content,
                system_prompt=args.system_prompt,
                created_by=args.created_by,
            )
        )
        print(prompt.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a prompt version.")
    parser.add_argument("project")
    parser.add_argument("prompt_key")
    parser.add_argument("content")
    parser.add_argument("--version", type=int)
    parser.add_argument("--system-prompt")
    parser.add_argument("--created-by", default="script")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()

