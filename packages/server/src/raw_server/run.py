"""Server runner with uvicorn integration and CLI support.

Provides functions for running FastAPI applications with uvicorn, including
support for command-line interfaces and programmatic server execution.
"""

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI

from raw_server.config import ServerConfig

logger = logging.getLogger(__name__)


def run_server(
    app: FastAPI | str,
    config: ServerConfig | None = None,
    **uvicorn_kwargs: Any,
) -> None:
    """Run a FastAPI application with uvicorn.

    Starts the uvicorn ASGI server with the provided application and
    configuration. Supports both FastAPI app instances and import strings.

    Why: Provides a consistent way to run FastAPI apps with proper
    configuration, avoiding boilerplate and ensuring production-ready
    defaults are applied.

    Args:
        app: FastAPI application instance or import string (e.g., "myapp:app").
        config: Server configuration (loads from env vars if None).
        **uvicorn_kwargs: Additional keyword arguments to pass to uvicorn.run().
            These override config values if provided.

    Example:
        ```python
        from raw_server import create_app, run_server, ServerConfig

        config = ServerConfig(host="0.0.0.0", port=8000)
        app = create_app(config)
        run_server(app, config)
        ```

        Or with import string:
        ```python
        run_server("myapp:app", config)
        ```
    """
    # Load config from environment if not provided
    if config is None:
        config = ServerConfig()

    # Build uvicorn configuration
    uvicorn_config = {
        "host": config.host,
        "port": config.port,
        "workers": config.workers,
        "reload": config.reload,
        "log_level": config.log_level,
        "access_log": config.access_log,
    }

    # Override with any provided kwargs
    uvicorn_config.update(uvicorn_kwargs)

    logger.info(
        "Starting uvicorn server",
        extra={
            "host": uvicorn_config["host"],
            "port": uvicorn_config["port"],
            "workers": uvicorn_config["workers"],
            "reload": uvicorn_config["reload"],
        },
    )

    # Run uvicorn
    try:
        uvicorn.run(app, **uvicorn_config)
    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
    except Exception as e:
        logger.exception("Server failed: %s", e)
        raise


def create_cli(
    app_factory: Any = None,
    app_import: str | None = None,
) -> None:
    """Create a CLI entry point for running the server.

    Provides a simple CLI interface that loads configuration from
    environment variables and starts the server.

    Why: Separates CLI concerns from application logic, making it
    easy to create command-line tools while keeping the core app
    testable and reusable.

    Args:
        app_factory: Optional function that creates a FastAPI app.
            If provided, will be called to create the app.
        app_import: Optional import string for the app (e.g., "myapp:app").
            If provided, uvicorn will import the app directly.
            One of app_factory or app_import must be provided.

    Example:
        Create a CLI script:
        ```python
        # cli.py
        from raw_server import create_cli, create_app

        def make_app():
            return create_app()

        if __name__ == "__main__":
            create_cli(app_factory=make_app)
        ```

        Or with import string:
        ```python
        if __name__ == "__main__":
            create_cli(app_import="myapp:app")
        ```

        Then run:
        ```bash
        export RAW_SERVER_HOST=0.0.0.0
        export RAW_SERVER_PORT=8000
        python cli.py
        ```
    """
    import sys

    if not app_factory and not app_import:
        print("Error: Either app_factory or app_import must be provided")
        sys.exit(1)

    # Load configuration from environment
    config = ServerConfig()

    # Setup logging
    logging.basicConfig(
        level=config.log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        if app_factory:
            # Create app using factory
            logger.info("Creating application using factory")
            app = app_factory()
            run_server(app, config)
        else:
            # Use import string (let uvicorn handle import)
            logger.info("Starting server with import string: %s", app_import)
            run_server(app_import, config)

    except Exception as e:
        logger.exception("Failed to start server: %s", e)
        sys.exit(1)


def run_with_reload(
    app_import: str,
    config: ServerConfig | None = None,
    reload_dirs: list[str] | None = None,
) -> None:
    """Run server with auto-reload for development.

    Starts uvicorn with reload mode enabled, watching specified
    directories for changes.

    Why: Development mode with auto-reload improves developer experience
    by automatically restarting the server when code changes.

    Args:
        app_import: Import string for the app (e.g., "myapp:app").
        config: Server configuration (loads from env vars if None).
        reload_dirs: Directories to watch for changes. If None, watches
            the directory containing the app module.

    Example:
        ```python
        run_with_reload(
            "myapp:app",
            reload_dirs=["src", "config"],
        )
        ```
    """
    if config is None:
        config = ServerConfig()

    # Force reload mode
    config.reload = True

    # Build reload configuration
    uvicorn_kwargs = {}
    if reload_dirs:
        uvicorn_kwargs["reload_dirs"] = reload_dirs

    logger.info(
        "Starting development server with auto-reload",
        extra={"reload_dirs": reload_dirs},
    )

    run_server(app_import, config, **uvicorn_kwargs)


# Example usage
if __name__ == "__main__":
    """Example CLI entry point.

    This demonstrates how to create a simple CLI for running a server.
    In practice, you would create a separate CLI script or use a proper
    CLI framework like Click or Typer.
    """
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Simple argument parsing
    if len(sys.argv) > 1:
        app_import = sys.argv[1]
    else:
        print("Usage: python -m raw_server.run <app_import>")
        print("Example: python -m raw_server.run myapp:app")
        sys.exit(1)

    # Load config and run
    config = ServerConfig()
    run_server(app_import, config)
