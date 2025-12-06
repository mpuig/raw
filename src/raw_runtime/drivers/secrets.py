"""Secret provider implementations."""

import os
from pathlib import Path

from raw_runtime.protocols.secrets import SecretProvider


class EnvVarSecretProvider:
    """Secret provider using environment variables.

    The simplest provider - reads directly from os.environ.
    """

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

    def has_secret(self, key: str) -> bool:
        return key in os.environ

    def require_secret(self, key: str) -> str:
        value = os.environ.get(key)
        if value is None:
            raise KeyError(f"Secret not found: {key}")
        return value


class DotEnvSecretProvider:
    """Secret provider that loads from .env files.

    Searches for .env in the specified directory and parent directories.
    Caches loaded values but does not override existing environment variables.
    """

    def __init__(self, search_path: Path | None = None) -> None:
        """Initialize with optional search path.

        Args:
            search_path: Starting directory to search for .env
                        (defaults to current working directory)
        """
        self._search_path = search_path or Path.cwd()
        self._loaded = False
        self._secrets: dict[str, str] = {}

    def _ensure_loaded(self) -> None:
        """Load .env file if not already loaded."""
        if self._loaded:
            return

        self._loaded = True
        env_file = self._find_env_file()
        if env_file:
            self._secrets = self._parse_env_file(env_file)

    def _find_env_file(self) -> Path | None:
        """Find .env file in search path or parent directories."""
        current = self._search_path
        home = Path.home()

        while current >= home:
            candidate = current / ".env"
            if candidate.exists():
                return candidate
            if current == current.parent:
                break
            current = current.parent

        return None

    def _parse_env_file(self, path: Path) -> dict[str, str]:
        """Parse .env file into dict."""
        secrets = {}

        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")

            if key and value:
                secrets[key] = value

        return secrets

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        # Environment variables take precedence
        if key in os.environ:
            return os.environ[key]

        self._ensure_loaded()
        return self._secrets.get(key, default)

    def has_secret(self, key: str) -> bool:
        if key in os.environ:
            return True
        self._ensure_loaded()
        return key in self._secrets

    def require_secret(self, key: str) -> str:
        value = self.get_secret(key)
        if value is None:
            raise KeyError(f"Secret not found: {key}")
        return value


class ChainedSecretProvider:
    """Secret provider that chains multiple providers.

    Tries each provider in order until a secret is found.
    Useful for layered configuration (env vars -> .env -> cloud).
    """

    def __init__(self, providers: list[SecretProvider]) -> None:
        """Initialize with list of providers to chain.

        Args:
            providers: Providers to try in order
        """
        self._providers = providers

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        for provider in self._providers:
            value = provider.get_secret(key)
            if value is not None:
                return value
        return default

    def has_secret(self, key: str) -> bool:
        return any(p.has_secret(key) for p in self._providers)

    def require_secret(self, key: str) -> str:
        for provider in self._providers:
            if provider.has_secret(key):
                return provider.require_secret(key)
        raise KeyError(f"Secret not found: {key}")


class CachingSecretProvider:
    """Secret provider wrapper that caches lookups.

    Wraps another provider and caches results to avoid
    repeated lookups (useful for cloud providers with API calls).
    """

    def __init__(self, provider: SecretProvider) -> None:
        """Initialize with provider to wrap.

        Args:
            provider: Underlying provider to cache
        """
        self._provider = provider
        self._cache: dict[str, str | None] = {}

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        if key in self._cache:
            value = self._cache[key]
            return value if value is not None else default

        value = self._provider.get_secret(key)
        self._cache[key] = value
        return value if value is not None else default

    def has_secret(self, key: str) -> bool:
        if key in self._cache:
            return self._cache[key] is not None
        return self._provider.has_secret(key)

    def require_secret(self, key: str) -> str:
        if key in self._cache:
            value = self._cache[key]
            if value is None:
                raise KeyError(f"Secret not found: {key}")
            return value

        value = self._provider.require_secret(key)
        self._cache[key] = value
        return value

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
