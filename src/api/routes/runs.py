from __future__ import annotations

from fastapi import APIRouter

from db.session import session_scope
from services.status import StatusService
from services.capabilities import CapabilityService


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict:
    async with session_scope() as session:
        result = await StatusService(session).get_run_status(run_id)
        return result.model_dump(mode="json")


@router.get("/meta/supported-metrics")
async def supported_metrics() -> dict:
    return CapabilityService().get_supported_metrics().model_dump(mode="json")

