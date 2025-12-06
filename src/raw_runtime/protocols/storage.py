"""StorageBackend protocol definition."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends.

    Implementations handle the mechanics of storing and retrieving
    workflow artifacts, manifests, and logs to various backends.
    """

    def save_artifact(
        self,
        run_id: str,
        filename: str,
        content: bytes | str,
    ) -> str:
        """Save an artifact file.

        Args:
            run_id: Unique identifier for the workflow run
            filename: Name of the artifact file
            content: File content (bytes or string)

        Returns:
            Path or URI where artifact was saved
        """
        ...

    def load_artifact(
        self,
        run_id: str,
        filename: str,
    ) -> bytes:
        """Load an artifact file.

        Args:
            run_id: Unique identifier for the workflow run
            filename: Name of the artifact file

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If artifact doesn't exist
        """
        ...

    def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifacts for a run.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            List of artifact filenames
        """
        ...

    def save_manifest(
        self,
        run_id: str,
        manifest: dict[str, Any],
    ) -> str:
        """Save run manifest.

        Args:
            run_id: Unique identifier for the workflow run
            manifest: Manifest data to save

        Returns:
            Path or URI where manifest was saved
        """
        ...

    def load_manifest(self, run_id: str) -> dict[str, Any]:
        """Load run manifest.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            Manifest data

        Raises:
            FileNotFoundError: If manifest doesn't exist
        """
        ...

    def save_log(
        self,
        run_id: str,
        content: str,
        append: bool = False,
    ) -> str:
        """Save or append to run log.

        Args:
            run_id: Unique identifier for the workflow run
            content: Log content
            append: If True, append to existing log

        Returns:
            Path or URI where log was saved
        """
        ...

    def load_log(self, run_id: str) -> str:
        """Load run log.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            Log content

        Raises:
            FileNotFoundError: If log doesn't exist
        """
        ...
