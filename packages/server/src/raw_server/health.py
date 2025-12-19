"""Health check system for monitoring service dependencies.

Provides a flexible health check registry that can monitor databases, queues,
external services, and custom components. Aggregates individual checks into
overall system health status.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration.

    Why: Explicit status types allow clients to distinguish between healthy,
    degraded, and unhealthy states for better operational decisions.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a single health check.

    Immutable record of a health check execution with status, timing,
    and optional error information.

    Why: Immutable results prevent side effects and make it easy to
    aggregate and track health check history.
    """

    name: str
    status: HealthStatus
    timestamp: datetime
    duration_ms: float
    message: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class HealthCheckResponse:
    """Aggregated health check response.

    Contains overall system health status and individual check results.

    Why: Aggregated response provides both high-level status for load
    balancers and detailed diagnostics for troubleshooting.
    """

    status: HealthStatus
    timestamp: datetime
    checks: dict[str, CheckResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
            "metadata": self.metadata,
        }


# Type alias for health check functions
HealthCheckFunc = Callable[[], Awaitable[CheckResult]]


class HealthCheck:
    """Health check registry and aggregator.

    Manages registration of individual health checks and provides methods
    to execute them and aggregate results into overall system health.

    Why: Centralized health check management enables consistent monitoring
    across all service dependencies with flexible check registration.

    Example:
        ```python
        health = HealthCheck()

        # Register database check
        async def check_database() -> CheckResult:
            start = datetime.now()
            try:
                await db.execute("SELECT 1")
                duration = (datetime.now() - start).total_seconds() * 1000
                return CheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    timestamp=datetime.now(),
                    duration_ms=duration,
                )
            except Exception as e:
                duration = (datetime.now() - start).total_seconds() * 1000
                return CheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.now(),
                    duration_ms=duration,
                    error=str(e),
                )

        health.register("database", check_database)

        # Execute all checks
        result = await health.check()
        ```
    """

    def __init__(self) -> None:
        """Initialize health check registry."""
        self._checks: dict[str, HealthCheckFunc] = {}

    def register(self, name: str, check_func: HealthCheckFunc) -> None:
        """Register a health check function.

        Args:
            name: Unique identifier for this check.
            check_func: Async function that returns a CheckResult.

        Raises:
            ValueError: If a check with this name already exists.
        """
        if name in self._checks:
            raise ValueError(f"Health check '{name}' already registered")

        self._checks[name] = check_func
        logger.info("Registered health check: %s", name)

    def unregister(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Name of check to remove.
        """
        if name in self._checks:
            del self._checks[name]
            logger.info("Unregistered health check: %s", name)

    async def check(self, timeout: float = 5.0) -> HealthCheckResponse:
        """Execute all registered health checks.

        Runs all checks concurrently and aggregates results. Individual check
        failures don't prevent other checks from running.

        Why: Concurrent execution minimizes total check time while providing
        comprehensive health status across all dependencies.

        Args:
            timeout: Maximum time in seconds to wait for all checks.

        Returns:
            Aggregated health check response with overall status.
        """
        timestamp = datetime.now()
        results: dict[str, CheckResult] = {}

        if not self._checks:
            # No checks registered, consider system healthy
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=timestamp,
                checks={},
                metadata={"message": "No health checks registered"},
            )

        # Execute all checks concurrently
        check_tasks = {
            name: asyncio.create_task(self._execute_check(name, func))
            for name, func in self._checks.items()
        }

        try:
            # Wait for all checks with timeout
            done, pending = await asyncio.wait(
                check_tasks.values(),
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED,
            )

            # Cancel any pending checks
            for task in pending:
                task.cancel()

            # Collect results
            for name, task in check_tasks.items():
                if task in done:
                    results[name] = await task
                else:
                    # Check timed out
                    results[name] = CheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        timestamp=datetime.now(),
                        duration_ms=timeout * 1000,
                        error=f"Health check timed out after {timeout}s",
                    )

        except Exception as e:
            logger.exception("Error executing health checks")
            # Return unhealthy if check execution fails
            return HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=timestamp,
                checks={},
                metadata={"error": str(e)},
            )

        # Aggregate status
        overall_status = self._aggregate_status(results)

        return HealthCheckResponse(
            status=overall_status,
            timestamp=timestamp,
            checks=results,
        )

    async def check_readiness(self, timeout: float = 5.0) -> bool:
        """Check if the service is ready to accept traffic.

        Simpler boolean check useful for readiness probes in orchestrators.

        Why: Kubernetes and other orchestrators need simple boolean readiness
        to determine if a pod should receive traffic.

        Args:
            timeout: Maximum time in seconds to wait for checks.

        Returns:
            True if all checks are healthy or degraded, False otherwise.
        """
        result = await health.check(timeout=timeout)
        return result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    async def check_liveness(self) -> bool:
        """Check if the service is alive.

        Lightweight check that doesn't test dependencies, only verifies
        the service process is responsive.

        Why: Liveness probes should be fast and not test external dependencies
        to avoid cascading failures during transient issues.

        Returns:
            Always True unless the process is completely frozen.
        """
        return True

    async def _execute_check(self, name: str, check_func: HealthCheckFunc) -> CheckResult:
        """Execute a single health check with error handling.

        Args:
            name: Name of the check.
            check_func: Check function to execute.

        Returns:
            CheckResult with status and timing information.
        """
        try:
            result = await check_func()
            return result
        except Exception as e:
            logger.exception("Health check '%s' failed", name)
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                duration_ms=0.0,
                error=str(e),
            )

    def _aggregate_status(self, results: dict[str, CheckResult]) -> HealthStatus:
        """Aggregate individual check results into overall status.

        Rules:
        - If any check is UNHEALTHY, overall is UNHEALTHY
        - If any check is DEGRADED and none UNHEALTHY, overall is DEGRADED
        - If all checks are HEALTHY, overall is HEALTHY

        Why: Conservative aggregation ensures system reports unhealthy if
        any critical dependency fails, while still distinguishing degraded
        performance from complete failure.

        Args:
            results: Dictionary of check results.

        Returns:
            Aggregated health status.
        """
        if not results:
            return HealthStatus.HEALTHY

        statuses = [result.status for result in results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


# Global health check instance
health = HealthCheck()
