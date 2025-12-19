"""RAW Server - Production-ready FastAPI server for RAW Platform.

This package provides a production-ready FastAPI server with:
- Health check endpoints for monitoring and orchestration
- Middleware for logging, error handling, and telemetry
- CORS configuration with environment variable support
- Lifecycle management for startup/shutdown tasks
- Uvicorn integration with CLI support
"""

__version__ = "0.1.0"

# Re-export commonly used items at package level
from raw_server.app import create_app
from raw_server.config import CORSConfig, ServerConfig
from raw_server.health import (
    CheckResult,
    HealthCheck,
    HealthCheckResponse,
    HealthStatus,
    health,
)
from raw_server.middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    TelemetryMiddleware,
    setup_middleware,
)
from raw_server.run import create_cli, run_server, run_with_reload

__all__ = [
    # App factory
    "create_app",
    # Configuration
    "ServerConfig",
    "CORSConfig",
    # Health checks
    "HealthCheck",
    "HealthCheckResponse",
    "CheckResult",
    "HealthStatus",
    "health",
    # Middleware
    "ErrorHandlingMiddleware",
    "RequestLoggingMiddleware",
    "TelemetryMiddleware",
    "setup_middleware",
    # Server runner
    "run_server",
    "run_with_reload",
    "create_cli",
]
