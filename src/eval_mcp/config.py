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
    api_url: str = Field(
        default="https://eval-mcp.onrender.com",
        alias="EVAL_MCP_API_URL",
        description="Backend API URL. Override for self-hosting.",
    )
    api_key: str | None = Field(default=None, alias="EVAL_MCP_API_KEY")
    timeout_seconds: float = Field(default=30.0, alias="EVAL_MCP_TIMEOUT_SECONDS")
    default_project: str | None = Field(default=None, alias="EVAL_MCP_DEFAULT_PROJECT")
    mcp_transport: str = Field(default="stdio", alias="MCP_TRANSPORT")
    max_concurrent_requests: int = Field(
        default=20,
        alias="EVAL_MCP_MAX_CONCURRENT_REQUESTS",
        description="Maximum number of concurrent outbound API requests.",
    )
    max_response_bytes: int = Field(
        default=10 * 1024 * 1024,
        alias="EVAL_MCP_MAX_RESPONSE_BYTES",
        description="Maximum response body size in bytes (default 10 MiB).",
    )


@lru_cache(maxsize=1)
def get_mcp_settings() -> MCPClientSettings:
    return MCPClientSettings()
