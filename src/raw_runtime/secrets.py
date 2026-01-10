"""Secret management abstraction for workflow credentials.

Provides a protocol for retrieving secrets, enabling:
- Environment variable secrets (default)
- .env file loading
- Future: Cloud secret managers (AWS Secrets Manager, GCP Secret Manager, etc.)

Note: Protocol is in raw_runtime.protocols.secrets,
      Implementations are in raw_runtime.drivers.secrets.
      This module re-exports for backwards compatibility.
"""

from raw_runtime.container import RuntimeContainer
from raw_runtime.drivers.secrets import (
    CachingSecretProvider,
    ChainedSecretProvider,
    DotEnvSecretProvider,
    EnvVarSecretProvider,
)
from raw_runtime.protocols.secrets import SecretProvider

# Backward-compatible accessors that delegate to RuntimeContainer


def get_secret_provider() -> SecretProvider:
    """Get the current secret provider.

    Returns a ChainedSecretProvider with EnvVar and DotEnv by default.
    """
    return RuntimeContainer.secrets()


def set_secret_provider(provider: SecretProvider | None) -> None:
    """Set the global secret provider."""
    RuntimeContainer.set_secrets(provider)


def get_secret(key: str, default: str | None = None) -> str | None:
    """Convenience function to get a secret using the global provider."""
    return get_secret_provider().get_secret(key, default)


def require_secret(key: str) -> str:
    """Convenience function to require a secret using the global provider."""
    return get_secret_provider().require_secret(key)


__all__ = [
    "SecretProvider",
    "EnvVarSecretProvider",
    "DotEnvSecretProvider",
    "ChainedSecretProvider",
    "CachingSecretProvider",
    "get_secret_provider",
    "set_secret_provider",
    "get_secret",
    "require_secret",
]
