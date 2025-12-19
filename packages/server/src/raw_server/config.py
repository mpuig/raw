"""Server configuration with environment variable support.

Provides typed configuration models for server settings including host, port,
workers, logging, and CORS. Supports loading from environment variables for
12-factor app compliance.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSConfig(BaseSettings):
    """CORS configuration for cross-origin requests.

    Why: Separate CORS config allows fine-grained control over which origins,
    methods, and headers are allowed, essential for browser-based clients.
    """

    enabled: bool = Field(
        default=False,
        description="Enable CORS middleware"
    )
    allow_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed origins for CORS"
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP methods"
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP headers"
    )

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        case_sensitive=False,
    )


class ServerConfig(BaseSettings):
    """Server configuration with environment variable support.

    Loads configuration from environment variables with the RAW_SERVER_ prefix.
    Provides sensible defaults for local development while supporting production
    deployment scenarios.

    Why: Using pydantic-settings enables type-safe configuration loading from
    environment variables, supporting 12-factor app principles and making
    deployment flexible across different environments.

    Example:
        ```bash
        export RAW_SERVER_HOST=0.0.0.0
        export RAW_SERVER_PORT=8000
        export RAW_SERVER_WORKERS=4
        export RAW_SERVER_LOG_LEVEL=info
        ```

        ```python
        config = ServerConfig()  # Loads from env vars
        ```
    """

    host: str = Field(
        default="127.0.0.1",
        description="Server bind address"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes (uvicorn)"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload on code changes (development only)"
    )
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info",
        description="Logging level"
    )
    access_log: bool = Field(
        default=True,
        description="Enable uvicorn access logging"
    )

    # Server metadata
    title: str = Field(
        default="RAW Platform API",
        description="API title shown in docs"
    )
    description: str = Field(
        default="Production-ready FastAPI server for RAW Platform",
        description="API description shown in docs"
    )
    version: str = Field(
        default="0.1.0",
        description="API version"
    )

    # Feature flags
    enable_docs: bool = Field(
        default=True,
        description="Enable /docs and /redoc endpoints"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics endpoint"
    )

    # Timeouts and limits
    request_timeout: int = Field(
        default=60,
        description="Request timeout in seconds"
    )
    max_request_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum request body size in bytes"
    )

    # CORS configuration
    cors: CORSConfig = Field(
        default_factory=CORSConfig,
        description="CORS configuration"
    )

    model_config = SettingsConfigDict(
        env_prefix="RAW_SERVER_",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    @property
    def docs_url(self) -> str | None:
        """Return docs URL if enabled, None otherwise."""
        return "/docs" if self.enable_docs else None

    @property
    def redoc_url(self) -> str | None:
        """Return redoc URL if enabled, None otherwise."""
        return "/redoc" if self.enable_docs else None

    @property
    def openapi_url(self) -> str | None:
        """Return OpenAPI schema URL if docs enabled, None otherwise."""
        return "/openapi.json" if self.enable_docs else None
