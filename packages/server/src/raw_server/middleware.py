"""Middleware for request logging, error handling, and telemetry integration.

Provides reusable middleware components that can be added to any FastAPI
application for consistent logging, error handling, and observability.
"""

import logging
import time
import traceback
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from raw_core import PlatformError
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses.

    Logs request details (method, path, query params) and response details
    (status code, duration). Useful for debugging and monitoring.

    Why: Centralized request logging provides consistent audit trail and
    performance metrics without requiring per-endpoint logging code.

    Example:
        ```python
        app.add_middleware(RequestLoggingMiddleware)
        ```
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response from downstream handler.
        """
        # Generate request ID for correlation
        request_id = request.headers.get("X-Request-ID", f"req-{id(request)}")

        # Log incoming request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) if request.url.query else None,
                "client": request.client.host if request.client else None,
            },
        )

        # Track request timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
            )

            # Re-raise to let error handling middleware deal with it
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for catching exceptions and returning JSON error responses.

    Converts Python exceptions into consistent JSON error responses with
    appropriate HTTP status codes. Integrates with raw-core error hierarchy
    for structured error handling.

    Why: Centralized error handling ensures all exceptions are caught and
    formatted consistently, preventing unformatted 500 errors from reaching
    clients and leaking implementation details.

    Example:
        ```python
        app.add_middleware(ErrorHandlingMiddleware)
        ```
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with error handling.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response, either from handler or error formatter.
        """
        try:
            return await call_next(request)

        except PlatformError as e:
            # Handle known platform errors
            return self._format_platform_error(request, e)

        except ValueError as e:
            # Handle validation errors
            return self._format_validation_error(request, e)

        except Exception as e:
            # Handle unexpected errors
            return self._format_unexpected_error(request, e)

    def _format_platform_error(
        self,
        request: Request,
        error: PlatformError,
    ) -> JSONResponse:
        """Format platform error as JSON response.

        Args:
            request: HTTP request.
            error: Platform error instance.

        Returns:
            JSON response with error details.
        """
        # Determine HTTP status code based on error type
        status_code = self._get_status_code(error)

        # Log the error
        logger.error(
            "Platform error",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "status_code": status_code,
                "path": request.url.path,
            },
        )

        # Build error response
        error_detail = {
            "error": type(error).__name__,
            "message": str(error),
            "path": request.url.path,
        }

        return JSONResponse(
            status_code=status_code,
            content=error_detail,
        )

    def _format_validation_error(
        self,
        request: Request,
        error: ValueError,
    ) -> JSONResponse:
        """Format validation error as JSON response.

        Args:
            request: HTTP request.
            error: Validation error instance.

        Returns:
            JSON response with error details.
        """
        logger.warning(
            "Validation error",
            extra={
                "error_message": str(error),
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "ValidationError",
                "message": str(error),
                "path": request.url.path,
            },
        )

    def _format_unexpected_error(
        self,
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        """Format unexpected error as JSON response.

        Args:
            request: HTTP request.
            error: Exception instance.

        Returns:
            JSON response with error details.
        """
        # Log full traceback for debugging
        logger.exception(
            "Unexpected error",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "path": request.url.path,
                "traceback": traceback.format_exc(),
            },
        )

        # Return generic error to client (don't leak internals)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": request.url.path,
            },
        )

    def _get_status_code(self, error: PlatformError) -> int:
        """Determine HTTP status code for a platform error.

        Maps platform error types to appropriate HTTP status codes.

        Why: Different error types should return different HTTP status codes
        to help clients distinguish between client errors (4xx) and server
        errors (5xx).

        Args:
            error: Platform error instance.

        Returns:
            HTTP status code.
        """
        from raw_core import (
            ConfigurationError,
            LLMServiceError,
            MissingAPIKeyError,
            ServiceError,
            ToolExecutionError,
            ToolNotFoundError,
            ToolTimeoutError,
        )

        # Client errors (4xx)
        if isinstance(error, (MissingAPIKeyError, ConfigurationError)):
            return status.HTTP_401_UNAUTHORIZED
        elif isinstance(error, ToolNotFoundError):
            return status.HTTP_404_NOT_FOUND
        elif isinstance(error, (ToolTimeoutError, ToolExecutionError)):
            return status.HTTP_408_REQUEST_TIMEOUT

        # Service errors (5xx)
        elif isinstance(error, (ServiceError, LLMServiceError)):
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # Default to internal server error
        return status.HTTP_500_INTERNAL_SERVER_ERROR


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware for integrating OpenTelemetry tracing.

    Automatically creates spans for HTTP requests and adds relevant attributes
    for distributed tracing. Integrates with raw-telemetry package.

    Why: Automatic span creation ensures all HTTP requests are traced without
    requiring manual instrumentation in each endpoint.

    Example:
        ```python
        from raw_telemetry import TracingConfig, init_telemetry

        # Initialize telemetry
        config = TracingConfig(service_name="my-service")
        init_telemetry(config)

        # Add middleware
        app.add_middleware(TelemetryMiddleware)
        ```
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with telemetry tracing.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response from downstream handler.
        """
        try:
            # Try to import telemetry components
            from opentelemetry import trace
            from opentelemetry.trace import SpanKind, Status, StatusCode

            tracer = trace.get_tracer(__name__)
        except ImportError:
            # Telemetry not available, pass through
            return await call_next(request)

        # Create span for this request
        span_name = f"{request.method} {request.url.path}"

        with tracer.start_as_current_span(
            span_name,
            kind=SpanKind.SERVER,
        ) as span:
            # Add request attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.target", request.url.path)
            if request.client:
                span.set_attribute("http.client_ip", request.client.host)

            try:
                # Process request
                response = await call_next(request)

                # Add response attributes
                span.set_attribute("http.status_code", response.status_code)

                # Set span status based on HTTP status
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))
                else:
                    span.set_status(Status(StatusCode.OK))

                return response

            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


def setup_middleware(app: Any, enable_telemetry: bool = False) -> None:
    """Configure middleware stack for a FastAPI application.

    Adds middleware in the correct order (outermost to innermost):
    1. Telemetry (optional) - outermost for complete tracing
    2. Error handling - catch all exceptions
    3. Request logging - log after error handling

    Why: Middleware order matters. Error handling should be before logging
    so we can log errors properly, and telemetry should be outermost to
    capture the entire request lifecycle.

    Args:
        app: FastAPI application instance.
        enable_telemetry: Whether to enable telemetry middleware.

    Example:
        ```python
        app = FastAPI()
        setup_middleware(app, enable_telemetry=True)
        ```
    """
    # Add middleware in reverse order (last added = outermost)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)

    if enable_telemetry:
        app.add_middleware(TelemetryMiddleware)

    logger.info(
        "Middleware configured",
        extra={"telemetry_enabled": enable_telemetry},
    )
