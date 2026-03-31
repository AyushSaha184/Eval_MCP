from __future__ import annotations

from db.session import session_scope
from domain.schemas import AnnotationRequest
from services.runs import RunService


async def annotate_run(request: AnnotationRequest) -> dict:
    async with session_scope() as session:
        annotation = await RunService(session).annotate_run(request)
        return {"ok": True, **annotation.model_dump(mode="json")}

