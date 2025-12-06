"""SecretProvider protocol definition."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretProvider(Protocol):
    """Protocol for secret providers.

    Implementations handle the mechanics of retrieving secrets
    from various backends.
    """

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Get a secret value by key.

        Args:
            key: Secret identifier (e.g., "ANTHROPIC_API_KEY")
            default: Value to return if secret not found

        Returns:
            Secret value, or default if not found
        """
        ...

    def has_secret(self, key: str) -> bool:
        """Check if a secret exists.

        Args:
            key: Secret identifier

        Returns:
            True if secret exists
        """
        ...

    def require_secret(self, key: str) -> str:
        """Get a secret, raising if not found.

        Args:
            key: Secret identifier

        Returns:
            Secret value

        Raises:
            KeyError: If secret not found
        """
        ...
