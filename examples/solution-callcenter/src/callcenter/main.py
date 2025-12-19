"""Entry point for call center solution.

Loads configuration, initializes services, and starts the server.
"""

import logging
import sys
from pathlib import Path

import uvicorn

from callcenter.app import create_callcenter_app
from callcenter.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the call center application.

    Why: Provides a single entry point that handles configuration loading,
    validation, and server startup.
    """
    try:
        # Load configuration from config.yaml and environment
        logger.info("Loading configuration...")
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        config = load_config(config_path)

        logger.info(
            "Configuration loaded",
            extra={
                "llm_model": config.llm.model,
                "server_host": config.server.host,
                "server_port": config.server.port,
            },
        )

        # Create FastAPI application
        logger.info("Creating application...")
        app = create_callcenter_app(config)

        # Start server
        logger.info(
            f"Starting server on {config.server.host}:{config.server.port}...",
        )

        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level.lower(),
            access_log=True,
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Application failed to start: {e}")
        sys.exit(1)


# Allow running as module: python -m callcenter.main
if __name__ == "__main__":
    main()


# Create app instance for ASGI servers (e.g., uvicorn callcenter.main:app)
try:
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    config = load_config(config_path)
    app = create_callcenter_app(config)
except Exception as e:
    logger.exception(f"Failed to create app instance: {e}")
    # Create a minimal app that shows the error
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def error_page():
        return {
            "error": "Configuration failed",
            "message": str(e),
            "help": "Check your config.yaml and .env files",
        }
