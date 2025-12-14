"""Environment configuration and provider detection for RAW.

Uses pydantic-settings for type-safe configuration with custom directory-tree
search for .env files. Searches from the current directory up to home.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class RawSettings(BaseSettings):
    """RAW environment settings with type-safe API key access.

    Uses pydantic-settings for automatic environment variable loading.
    The .env file is found by searching up the directory tree.
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM providers
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # Messaging providers
    slack_webhook_url: str | None = None

    # Data providers
    alphavantage_api_key: str | None = None
    news_api_key: str | None = None

    # RAW server
    raw_server_url: str | None = None


LLM_PROVIDERS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

MESSAGING_PROVIDERS = {
    "slack": "SLACK_WEBHOOK_URL",
}

DATA_PROVIDERS = {
    "alphavantage": "ALPHAVANTAGE_API_KEY",
    "newsapi": "NEWS_API_KEY",
}


def find_dotenv(start_path: Path | None = None) -> Path | None:
    """Find .env file by searching up the directory tree.

    Searches from start_path (or cwd) up to home directory.
    Returns the first .env file found, or None if not found.
    """
    current = start_path or Path.cwd()
    home = Path.home()

    while current >= home:
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        if current == current.parent:
            break
        current = current.parent

    return None


@lru_cache(maxsize=1)
def get_settings() -> RawSettings:
    """Get cached RawSettings instance.

    Finds .env by searching up directory tree, then loads settings.
    Cached to avoid repeated file I/O.
    """
    env_file = find_dotenv()
    if env_file:
        return RawSettings(_env_file=env_file)
    return RawSettings()


def clear_settings_cache() -> None:
    """Clear the settings cache. Useful for testing."""
    get_settings.cache_clear()


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load environment variables from .env file.

    Searches for .env in current directory and parent directories up to home.
    Does not override existing environment variables.

    Returns dict of loaded variables.

    Note: This function is kept for backward compatibility.
    Prefer using get_settings() for type-safe access.
    """
    env_file = find_dotenv(path)
    if env_file is None:
        return {}

    loaded = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")

        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value

    return loaded


def get_available_llm_providers() -> list[str]:
    """Return list of LLM providers with configured API keys."""
    settings = get_settings()
    available = []
    if settings.anthropic_api_key:
        available.append("anthropic")
    if settings.openai_api_key:
        available.append("openai")
    if settings.gemini_api_key:
        available.append("gemini")
    return available


def get_preferred_llm_provider() -> str | None:
    """Return the preferred available LLM provider.

    Priority: anthropic > openai > gemini
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    if settings.gemini_api_key:
        return "gemini"
    return None


def get_available_providers() -> dict[str, list[str]]:
    """Return all available providers grouped by category."""
    settings = get_settings()
    return {
        "llm": get_available_llm_providers(),
        "messaging": ["slack"] if settings.slack_webhook_url else [],
        "data": [
            name
            for name, has_key in [
                ("alphavantage", settings.alphavantage_api_key),
                ("newsapi", settings.news_api_key),
            ]
            if has_key
        ],
    }


# Maps provider names to their settings attribute names
_PROVIDER_ATTRS = {
    "llm": {
        "anthropic": "anthropic_api_key",
        "openai": "openai_api_key",
        "gemini": "gemini_api_key",
    },
    "messaging": {
        "slack": "slack_webhook_url",
    },
    "data": {
        "alphavantage": "alphavantage_api_key",
        "newsapi": "news_api_key",
    },
}


def require_provider(provider: str, category: str = "llm") -> str:
    """Get API key for a provider, raising if not available."""
    category_attrs = _PROVIDER_ATTRS.get(category)
    if not category_attrs:
        raise ValueError(f"Unknown category: {category}")

    attr_name = category_attrs.get(provider)
    if not attr_name:
        raise ValueError(f"Unknown provider: {provider} in category {category}")

    settings = get_settings()
    key = getattr(settings, attr_name)
    if not key:
        env_var = attr_name.upper()
        raise ValueError(f"{provider} API key not configured. Set {env_var} in your .env file.")

    return key


def ensure_env_loaded() -> None:
    """Ensure .env is loaded. Call at workflow/tool startup.

    Note: With pydantic-settings, this is mostly for backward compatibility.
    The settings are loaded lazily on first access to get_settings().
    """
    load_dotenv()
