from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = "eval-mcp"
    api_url: str = Field(default="http://127.0.0.1:8000", alias="EVAL_MCP_API_URL")
    api_key: str | None = Field(default=None, alias="EVAL_MCP_API_KEY")
    timeout_seconds: float = Field(default=30.0, alias="EVAL_MCP_TIMEOUT_SECONDS")
    default_project: str | None = Field(default=None, alias="EVAL_MCP_DEFAULT_PROJECT")
    mcp_transport: str = Field(default="stdio", alias="MCP_TRANSPORT")


@lru_cache(maxsize=1)
def get_mcp_settings() -> MCPClientSettings:
    return MCPClientSettings()
