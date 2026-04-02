from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = "Eval_MCP"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./eval_mcp.db",
        alias="DATABASE_URL",
    )
    queue_backend: Literal["database_polling", "redis"] = Field(
        default="database_polling",
        alias="QUEUE_BACKEND",
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    redis_queue_name: str = Field(default="eval_mcp:runs", alias="REDIS_QUEUE_NAME")
    worker_poll_interval_seconds: float = Field(
        default=1.0,
        alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_max_retries: int = Field(default=2, alias="WORKER_MAX_RETRIES")
    storage_provider: Literal["local", "s3", "b2"] = Field(
        default="local",
        alias="STORAGE_PROVIDER",
    )
    local_artifact_directory: str = Field(
        default="./.artifacts",
        alias="LOCAL_ARTIFACT_DIRECTORY",
    )
    default_model_provider: str = Field(
        default="stub",
        alias="DEFAULT_MODEL_PROVIDER",
    )
    default_model_name: str = Field(
        default="stub-evaluator",
        alias="DEFAULT_MODEL_NAME",
    )
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    google_ai_studio_api_key: str | None = Field(default=None, alias="GOOGLE_AI_STUDIO_API_KEY")
    google_api_base: str = Field(default="https://generativelanguage.googleapis.com", alias="GOOGLE_API_BASE")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_api_base: str = Field(default="https://api.anthropic.com", alias="ANTHROPIC_API_BASE")
    anthropic_api_version: str = Field(default="2023-06-01", alias="ANTHROPIC_API_VERSION")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_api_base: str = Field(default="https://api.openai.com/v1", alias="OPENAI_API_BASE")
    openai_organization: str | None = Field(default=None, alias="OPENAI_ORG_ID")
    model_request_timeout_seconds: float = Field(default=60.0, alias="MODEL_REQUEST_TIMEOUT_SECONDS")
    judge_request_timeout_seconds: float = Field(default=60.0, alias="JUDGE_REQUEST_TIMEOUT_SECONDS")
    use_live_deepeval: bool = Field(default=False, alias="USE_LIVE_DEEPEVAL")
    use_live_ragas: bool = Field(default=False, alias="USE_LIVE_RAGAS")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_region: str | None = Field(default=None, alias="S3_REGION")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(
        default=None,
        alias="S3_SECRET_ACCESS_KEY",
    )
    b2_bucket: str | None = Field(default=None, alias="B2_BUCKET")
    b2_region: str | None = Field(default=None, alias="B2_REGION")
    b2_endpoint_url: str | None = Field(default=None, alias="B2_ENDPOINT_URL")
    b2_key_id: str | None = Field(default=None, alias="B2_KEY_ID")
    b2_application_key: str | None = Field(default=None, alias="B2_APPLICATION_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    mcp_transport: Literal["stdio"] = Field(default="stdio", alias="MCP_TRANSPORT")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: str | None = Field(default=None, alias="EVAL_MCP_API_KEY")
    api_key_ring_raw: str | None = Field(default=None, alias="EVAL_MCP_API_KEYS")
    dashboard_host: str = Field(default="127.0.0.1", alias="DASHBOARD_HOST")
    dashboard_port: int = Field(default=8501, alias="DASHBOARD_PORT")
    testing: bool = False

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def valid_api_keys(self) -> list[str]:
        keys: list[str] = []
        if self.api_key:
            keys.append(self.api_key)
        if self.api_key_ring_raw:
            keys.extend(item.strip() for item in self.api_key_ring_raw.split(",") if item.strip())
        # Preserve order for rotation, but deduplicate.
        seen: set[str] = set()
        deduped: list[str] = []
        for key in keys:
            if key and key not in seen:
                seen.add(key)
                deduped.append(key)
        return deduped

    @property
    def object_storage_bucket(self) -> str | None:
        if self.storage_provider == "b2":
            return self.b2_bucket or self.s3_bucket
        return self.s3_bucket

    @property
    def object_storage_region(self) -> str | None:
        if self.storage_provider == "b2":
            return self.b2_region or self.s3_region
        return self.s3_region

    @property
    def object_storage_endpoint_url(self) -> str | None:
        if self.storage_provider == "b2":
            return self.b2_endpoint_url or self.s3_endpoint_url
        return self.s3_endpoint_url

    @property
    def object_storage_access_key_id(self) -> str | None:
        if self.storage_provider == "b2":
            return self.b2_key_id or self.s3_access_key_id
        return self.s3_access_key_id

    @property
    def object_storage_secret_access_key(self) -> str | None:
        if self.storage_provider == "b2":
            return self.b2_application_key or self.s3_secret_access_key
        return self.s3_secret_access_key

    @property
    def effective_google_api_key(self) -> str | None:
        return self.google_ai_studio_api_key or self.google_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
