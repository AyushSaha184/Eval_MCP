from __future__ import annotations

from services.capabilities import CapabilityService


async def get_supported_metrics() -> dict:
    response = CapabilityService().get_supported_metrics()
    return {"ok": True, **response.model_dump(mode="json")}

