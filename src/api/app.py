from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging import setup_logging
from api.routes.auth import router as auth_router
from api.routes.projects import router as projects_router
from api.routes.runs import router as runs_router
from api.routes.v1 import router as v1_router
from core.errors import EvalMCPError


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="Eval_MCP API", version="0.1.0")

    @app.exception_handler(EvalMCPError)
    async def handle_eval_mcp_error(_, exc: EvalMCPError) -> JSONResponse:
        status_code = 401 if exc.code == "unauthorized" else 400
        return JSONResponse(
            status_code=status_code,
            content={
                "ok": False,
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    app.include_router(projects_router)
    app.include_router(runs_router)
    app.include_router(auth_router)
    app.include_router(v1_router)

    return app


app = create_app()
