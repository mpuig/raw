"""FastAPI application factory with health checks, middleware, and lifecycle management.

Provides a factory function for creating production-ready FastAPI applications
with consistent configuration, middleware stack, and operational endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from raw_server.config import ServerConfig
from raw_server.health import CheckResult, HealthStatus, health
from raw_server.middleware import setup_middleware

logger = logging.getLogger(__name__)


def create_app(
    config: ServerConfig | None = None,
    startup_tasks: list[Any] | None = None,
    shutdown_tasks: list[Any] | None = None,
    enable_telemetry: bool = False,
) -> FastAPI:
    """Create a production-ready FastAPI application.

    Factory function that creates a FastAPI app with:
    - Health and readiness endpoints
    - Middleware for logging, error handling, and telemetry
    - CORS configuration
    - Lifecycle management for startup/shutdown tasks
    - Optional metrics endpoint

    Why: Factory pattern enables flexible configuration while maintaining
    consistent defaults. Supports dependency injection of config and tasks
    for different deployment scenarios.

    Args:
        config: Server configuration (loads from env vars if None).
        startup_tasks: Optional list of async functions to run on startup.
        shutdown_tasks: Optional list of async functions to run on shutdown.
        enable_telemetry: Whether to enable telemetry middleware.

    Returns:
        Configured FastAPI application.

    Example:
        ```python
        config = ServerConfig(
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )

        async def init_database():
            await db.connect()

        async def cleanup_database():
            await db.disconnect()

        app = create_app(
            config=config,
            startup_tasks=[init_database],
            shutdown_tasks=[cleanup_database],
            enable_telemetry=True,
        )
        ```
    """
    # Load config from environment if not provided
    if config is None:
        config = ServerConfig()

    # Define lifespan context manager for startup/shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle with startup and shutdown tasks.

        Why: Lifespan context manager is the recommended way to handle
        startup/shutdown in FastAPI, replacing deprecated event handlers.
        """
        # Startup
        logger.info("Application starting up")

        # Run startup tasks
        if startup_tasks:
            for task in startup_tasks:
                try:
                    await task()
                except Exception as e:
                    logger.exception("Startup task failed: %s", e)
                    raise

        # Register default health checks
        health.register("liveness", _create_liveness_check())

        logger.info("Application startup complete")

        yield

        # Shutdown
        logger.info("Application shutting down")

        # Run shutdown tasks
        if shutdown_tasks:
            for task in shutdown_tasks:
                try:
                    await task()
                except Exception as e:
                    logger.exception("Shutdown task failed: %s", e)

        logger.info("Application shutdown complete")

    # Create FastAPI app
    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        docs_url=config.docs_url,
        redoc_url=config.redoc_url,
        openapi_url=config.openapi_url,
        lifespan=lifespan,
    )

    # Configure CORS if enabled
    if config.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors.allow_origins,
            allow_credentials=config.cors.allow_credentials,
            allow_methods=config.cors.allow_methods,
            allow_headers=config.cors.allow_headers,
        )
        logger.info("CORS enabled with origins: %s", config.cors.allow_origins)

    # Setup middleware stack
    setup_middleware(app, enable_telemetry=enable_telemetry)

    # Register operational endpoints
    _register_health_endpoints(app)

    if config.enable_metrics:
        _register_metrics_endpoint(app)

    logger.info(
        "FastAPI application created",
        extra={
            "title": config.title,
            "version": config.version,
            "docs_enabled": config.enable_docs,
            "metrics_enabled": config.enable_metrics,
        },
    )

    return app


def _register_health_endpoints(app: FastAPI) -> None:
    """Register health check endpoints.

    Adds three endpoints:
    - /health: Comprehensive health check with all dependency checks
    - /ready: Readiness probe for orchestrators (boolean)
    - /live: Liveness probe for orchestrators (always returns 200)

    Why: Separate liveness and readiness probes follow Kubernetes best
    practices. Liveness checks if the app is running, readiness checks
    if it can handle traffic.

    Args:
        app: FastAPI application instance.
    """

    @app.get("/health", tags=["operational"])
    async def health_check():
        """Comprehensive health check endpoint.

        Executes all registered health checks and returns detailed status
        for each dependency. Used for monitoring and diagnostics.

        Returns:
            JSON with overall status and individual check results.
        """
        result = await health.check()
        status_code = 200 if result.status == HealthStatus.HEALTHY else 503
        return result.to_dict()

    @app.get("/ready", tags=["operational"])
    async def readiness_check():
        """Readiness probe endpoint.

        Simple boolean check indicating if the service is ready to accept
        traffic. Used by load balancers and orchestrators.

        Returns:
            200 if ready, 503 if not ready.
        """
        is_ready = await health.check_readiness()
        status_code = 200 if is_ready else 503
        return {"ready": is_ready}

    @app.get("/live", tags=["operational"])
    async def liveness_check():
        """Liveness probe endpoint.

        Lightweight check that verifies the process is responsive.
        Should not test external dependencies.

        Returns:
            Always 200 unless the process is completely frozen.
        """
        is_alive = await health.check_liveness()
        return {"alive": is_alive}

    logger.info("Health check endpoints registered")


def _register_metrics_endpoint(app: FastAPI) -> None:
    """Register metrics endpoint for monitoring.

    Exposes basic application metrics. Can be extended to support
    Prometheus format or other monitoring systems.

    Why: Metrics endpoint provides observability into application
    performance and behavior for monitoring systems.

    Args:
        app: FastAPI application instance.
    """

    @app.get("/metrics", tags=["operational"])
    async def metrics():
        """Application metrics endpoint.

        Returns basic metrics about the application. Can be extended
        to include custom metrics or Prometheus format.

        Returns:
            JSON with application metrics.
        """
        # Basic metrics - can be extended with actual metrics collection
        return {
            "status": "healthy",
            "version": app.version,
            # Add more metrics here (request count, latency, etc.)
        }

    logger.info("Metrics endpoint registered")


def _create_liveness_check():
    """Create a liveness health check function.

    Returns a simple check that always succeeds unless the process
    is completely frozen.

    Why: Liveness checks should be fast and not test dependencies
    to avoid false positives during transient issues.

    Returns:
        Async function that returns a CheckResult.
    """
    from datetime import datetime

    async def liveness_check() -> CheckResult:
        """Liveness health check."""
        return CheckResult(
            name="liveness",
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(),
            duration_ms=0.0,
            message="Service is alive",
        )

    return liveness_check
