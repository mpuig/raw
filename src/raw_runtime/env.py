"""Environment configuration and provider detection for RAW."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProviderConfig:
    """Configuration for an API provider."""

    name: str
    env_var: str
    is_available: bool


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


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load environment variables from .env file.

    Searches for .env in current directory and parent directories up to home.
    Does not override existing environment variables.

    Returns dict of loaded variables.
    """
    if path is None:
        path = Path.cwd()

    loaded = {}
    env_file = None

    current = path
    home = Path.home()
    while current >= home:
        candidate = current / ".env"
        if candidate.exists():
            env_file = candidate
            break
        if current == current.parent:
            break
        current = current.parent

    if env_file is None:
        return loaded

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
    return [name for name, env_var in LLM_PROVIDERS.items() if os.environ.get(env_var)]


def get_preferred_llm_provider() -> str | None:
    """Return the preferred available LLM provider.

    Priority: anthropic > openai > gemini
    """
    for provider in ["anthropic", "openai", "gemini"]:
        if os.environ.get(LLM_PROVIDERS[provider]):
            return provider
    return None


def get_available_providers() -> dict[str, list[str]]:
    """Return all available providers grouped by category."""
    return {
        "llm": get_available_llm_providers(),
        "messaging": [
            name for name, env_var in MESSAGING_PROVIDERS.items() if os.environ.get(env_var)
        ],
        "data": [name for name, env_var in DATA_PROVIDERS.items() if os.environ.get(env_var)],
    }


def require_provider(provider: str, category: str = "llm") -> str:
    """Get API key for a provider, raising if not available."""
    providers = {
        "llm": LLM_PROVIDERS,
        "messaging": MESSAGING_PROVIDERS,
        "data": DATA_PROVIDERS,
    }

    env_var = providers.get(category, {}).get(provider)
    if not env_var:
        raise ValueError(f"Unknown provider: {provider} in category {category}")

    key = os.environ.get(env_var)
    if not key:
        raise ValueError(f"{provider} API key not configured. Set {env_var} in your .env file.")

    return key


def ensure_env_loaded() -> None:
    """Ensure .env is loaded. Call at workflow/tool startup."""
    load_dotenv()
