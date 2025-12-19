# raw-server

Production-ready FastAPI server for RAW Platform with health checks, middleware, and telemetry.

## Overview

Provides a complete FastAPI server setup with operational best practices including health checks, structured logging, error handling, CORS configuration, and telemetry integration. Designed for production deployments with Kubernetes, Docker, and cloud platforms.

## Installation

```bash
uv add raw-server
```

## Quick start

### Basic server

```python
from raw_server import create_app, run_server

# Create app with defaults (config from environment)
app = create_app()

# Run server
run_server(app)
```

### Custom configuration

```python
from raw_server import create_app, run_server, ServerConfig

# Configure server
config = ServerConfig(
    host="0.0.0.0",
    port=8000,
    workers=4,
    log_level="info",
    title="My API",
    description="My production API",
)

# Enable CORS
config.cors.enabled = True
config.cors.allow_origins = ["https://example.com"]

# Create and run
app = create_app(config, enable_telemetry=True)
run_server(app, config)
```

### Environment variables

Configure server using environment variables with `RAW_SERVER_` prefix:

```bash
export RAW_SERVER_HOST=0.0.0.0
export RAW_SERVER_PORT=8000
export RAW_SERVER_WORKERS=4
export RAW_SERVER_LOG_LEVEL=info
export RAW_SERVER_RELOAD=false

# CORS configuration
export RAW_SERVER_CORS__ENABLED=true
export RAW_SERVER_CORS__ALLOW_ORIGINS='["https://example.com"]'

python myapp.py
```

## Features

### Health checks

The server provides three health check endpoints:

#### Comprehensive health check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-19T10:00:00Z",
  "checks": {
    "database": {
      "name": "database",
      "status": "healthy",
      "timestamp": "2025-12-19T10:00:00Z",
      "duration_ms": 5.2,
      "message": "Connected to PostgreSQL"
    },
    "redis": {
      "name": "redis",
      "status": "healthy",
      "timestamp": "2025-12-19T10:00:00Z",
      "duration_ms": 2.1,
      "message": "Connected to Redis"
    }
  }
}
```

#### Readiness probe

```bash
GET /ready
```

Returns 200 if ready to accept traffic, 503 otherwise.

#### Liveness probe

```bash
GET /live
```

Returns 200 if service is alive (process responsive).

### Custom health checks

Register custom health checks for your dependencies:

```python
from datetime import datetime
from raw_server import create_app, health, CheckResult, HealthStatus

app = create_app()

# Define check function
async def check_database() -> CheckResult:
    start = datetime.now()
    try:
        # Test database connection
        await db.execute("SELECT 1")
        duration = (datetime.now() - start).total_seconds() * 1000

        return CheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(),
            duration_ms=duration,
            message="Database connection healthy",
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

# Register check
health.register("database", check_database)
```

### Middleware

The server includes three middleware components:

1. **RequestLoggingMiddleware**: Logs all HTTP requests and responses with timing
2. **ErrorHandlingMiddleware**: Catches exceptions and returns JSON error responses
3. **TelemetryMiddleware**: Integrates with OpenTelemetry for distributed tracing

Middleware is automatically configured in the correct order when using `create_app()`.

### Lifecycle management

Add startup and shutdown tasks:

```python
from raw_server import create_app

async def startup_task():
    """Initialize resources on startup."""
    await db.connect()
    print("Database connected")

async def shutdown_task():
    """Cleanup resources on shutdown."""
    await db.disconnect()
    print("Database disconnected")

app = create_app(
    startup_tasks=[startup_task],
    shutdown_tasks=[shutdown_task],
)
```

### Error handling

Errors are automatically caught and formatted as JSON:

```python
from raw_core import ServiceError

@app.get("/example")
async def example():
    raise ServiceError("Something went wrong")

# Returns:
# {
#   "error": "ServiceError",
#   "message": "Something went wrong",
#   "path": "/example"
# }
```

### Telemetry integration

Enable OpenTelemetry tracing:

```python
from raw_server import create_app
from raw_telemetry import TracingConfig, init_telemetry

# Initialize telemetry
config = TracingConfig(
    service_name="my-service",
    exporter_endpoint="http://jaeger:4318",
)
init_telemetry(config)

# Create app with telemetry
app = create_app(enable_telemetry=True)
```

All HTTP requests will automatically create spans with relevant attributes.

## Usage patterns

### Development server with auto-reload

```python
from raw_server import run_with_reload

run_with_reload(
    "myapp:app",
    reload_dirs=["src", "config"],
)
```

### CLI entry point

```python
# cli.py
from raw_server import create_cli, create_app

def make_app():
    return create_app()

if __name__ == "__main__":
    create_cli(app_factory=make_app)
```

Run with:
```bash
export RAW_SERVER_HOST=0.0.0.0
export RAW_SERVER_PORT=8000
python cli.py
```

### Docker deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy application
COPY . .

# Configure via environment
ENV RAW_SERVER_HOST=0.0.0.0
ENV RAW_SERVER_PORT=8000
ENV RAW_SERVER_WORKERS=4
ENV RAW_SERVER_LOG_LEVEL=info

CMD ["python", "-m", "uvicorn", "myapp:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: my-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: RAW_SERVER_HOST
          value: "0.0.0.0"
        - name: RAW_SERVER_PORT
          value: "8000"
        - name: RAW_SERVER_WORKERS
          value: "1"  # Use 1 worker per pod
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Configuration reference

### ServerConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | str | "127.0.0.1" | Server bind address |
| `port` | int | 8000 | Server port |
| `workers` | int | 1 | Number of worker processes |
| `reload` | bool | False | Enable auto-reload (development) |
| `log_level` | str | "info" | Logging level (debug, info, warning, error, critical) |
| `access_log` | bool | True | Enable uvicorn access logging |
| `title` | str | "RAW Platform API" | API title in docs |
| `description` | str | "Production-ready FastAPI server for RAW Platform" | API description |
| `version` | str | "0.1.0" | API version |
| `enable_docs` | bool | True | Enable /docs and /redoc endpoints |
| `enable_metrics` | bool | True | Enable /metrics endpoint |
| `request_timeout` | int | 60 | Request timeout in seconds |
| `max_request_size` | int | 10485760 | Maximum request body size (10MB) |

### CORSConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | False | Enable CORS middleware |
| `allow_origins` | list[str] | ["*"] | Allowed origins |
| `allow_credentials` | bool | True | Allow credentials |
| `allow_methods` | list[str] | ["*"] | Allowed HTTP methods |
| `allow_headers` | list[str] | ["*"] | Allowed HTTP headers |

## Architecture

### Component separation

The package follows clean architecture with three layers:

1. **Configuration** (`config.py`): Type-safe config models with environment variable support
2. **Middleware** (`middleware.py`): HTTP middleware for logging, errors, and tracing
3. **Health** (`health.py`): Health check registry and aggregation
4. **App** (`app.py`): FastAPI factory with lifecycle management
5. **Runner** (`run.py`): Uvicorn integration and CLI support

### Dependency injection

The factory pattern enables flexible configuration:

```python
# Simple static configuration
app = create_app(config=ServerConfig())

# Dynamic configuration from environment
app = create_app()  # Loads from env vars

# Custom startup/shutdown
app = create_app(
    startup_tasks=[init_db, init_cache],
    shutdown_tasks=[cleanup_db, cleanup_cache],
)
```

### Middleware order

Middleware is added in the correct order (outermost to innermost):

1. Telemetry (optional) - outermost for complete tracing
2. CORS - early to handle preflight requests
3. Error handling - catch all exceptions
4. Request logging - log after error handling

## Dependencies

- `raw-core`: Core protocols, events, and errors
- `raw-state`: State management backends (for health checks)
- `raw-queue`: Queue backends (for health checks)
- `raw-telemetry`: OpenTelemetry integration
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `pydantic`: Data validation and settings
- `pydantic-settings`: Environment variable configuration

## Examples

### Complete production server

```python
from datetime import datetime
from raw_server import (
    create_app,
    run_server,
    ServerConfig,
    health,
    CheckResult,
    HealthStatus,
)

# Configure server
config = ServerConfig(
    host="0.0.0.0",
    port=8000,
    workers=4,
    log_level="info",
    title="Production API",
    enable_docs=False,  # Disable docs in production
)

# Enable CORS for specific origins
config.cors.enabled = True
config.cors.allow_origins = ["https://app.example.com"]
config.cors.allow_credentials = True

# Database and cache instances
db = MyDatabase()
cache = MyCache()

# Startup tasks
async def init_database():
    await db.connect()

async def init_cache():
    await cache.connect()

# Shutdown tasks
async def cleanup_database():
    await db.disconnect()

async def cleanup_cache():
    await cache.disconnect()

# Health checks
async def check_database() -> CheckResult:
    start = datetime.now()
    try:
        await db.ping()
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

async def check_cache() -> CheckResult:
    start = datetime.now()
    try:
        await cache.ping()
        duration = (datetime.now() - start).total_seconds() * 1000
        return CheckResult(
            name="cache",
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(),
            duration_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() * 1000
        return CheckResult(
            name="cache",
            status=HealthStatus.UNHEALTHY,
            timestamp=datetime.now(),
            duration_ms=duration,
            error=str(e),
        )

# Create app
app = create_app(
    config=config,
    startup_tasks=[init_database, init_cache],
    shutdown_tasks=[cleanup_database, cleanup_cache],
    enable_telemetry=True,
)

# Register health checks
health.register("database", check_database)
health.register("cache", check_cache)

# Add custom routes
@app.get("/api/status")
async def status():
    return {"status": "running", "version": "1.0.0"}

# Run server
if __name__ == "__main__":
    run_server(app, config)
```

### Integration with transport-webhook

```python
from raw_server import create_app, run_server
from transport_webhook import create_webhook_router

# Create base app
app = create_app()

# Add webhook transport
router = create_webhook_router(engine_factory)
app.include_router(router)

# Run
run_server(app)
```
