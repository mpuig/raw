"""Storage backend implementations."""

import json
from pathlib import Path
from typing import Any


def _serialize_for_storage(data: Any) -> str | bytes:
    """Serialize data for storage.

    Returns JSON string for dict/list, str as-is, raises for bytes.
    """
    if isinstance(data, bytes):
        raise ValueError("Cannot serialize bytes directly, use save_artifact")
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2, default=str)
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2, default=str)


class FileSystemStorage:
    """Storage backend using the local filesystem.

    Stores artifacts in a directory structure:
    base_path/
      {run_id}/
        results/
          {filename}
        manifest.json
        output.log
    """

    def __init__(
        self,
        base_path: Path | str | None = None,
        *,
        base_dir: Path | str | None = None,
    ) -> None:
        """Initialize with base storage path.

        Args:
            base_path: Root directory for all storage
            base_dir: Alias for base_path (for backwards compatibility)
        """
        path = base_path or base_dir or Path.cwd() / ".raw" / "runs"
        self._base_path = Path(path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        """Get path for a specific run."""
        return self._base_path / run_id

    def _artifacts_path(self, run_id: str) -> Path:
        """Get artifacts directory for a run."""
        return self._run_path(run_id) / "results"

    def save_artifact(
        self,
        run_id: str,
        filename: str,
        content: bytes | str,
    ) -> str:
        """Save an artifact file."""
        artifacts_dir = self._artifacts_path(run_id)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = artifacts_dir / filename
        if isinstance(content, bytes):
            artifact_path.write_bytes(content)
        else:
            artifact_path.write_text(content)

        return str(artifact_path)

    def load_artifact(
        self,
        run_id: str,
        filename: str,
    ) -> bytes:
        """Load an artifact file."""
        artifact_path = self._artifacts_path(run_id) / filename
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {filename}")
        return artifact_path.read_bytes()

    def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifacts for a run."""
        artifacts_dir = self._artifacts_path(run_id)
        if not artifacts_dir.exists():
            return []
        return [f.name for f in artifacts_dir.iterdir() if f.is_file()]

    def save_manifest(
        self,
        run_id: str,
        manifest: dict[str, Any],
    ) -> str:
        """Save run manifest."""
        run_path = self._run_path(run_id)
        run_path.mkdir(parents=True, exist_ok=True)

        manifest_path = run_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
        return str(manifest_path)

    def load_manifest(self, run_id: str) -> dict[str, Any]:
        """Load run manifest."""
        manifest_path = self._run_path(run_id) / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for run: {run_id}")
        return json.loads(manifest_path.read_text())

    def save_log(
        self,
        run_id: str,
        content: str,
        append: bool = False,
    ) -> str:
        """Save or append to run log."""
        run_path = self._run_path(run_id)
        run_path.mkdir(parents=True, exist_ok=True)

        log_path = run_path / "output.log"
        mode = "a" if append else "w"
        with log_path.open(mode) as f:
            f.write(content)
        return str(log_path)

    def load_log(self, run_id: str) -> str:
        """Load run log."""
        log_path = self._run_path(run_id) / "output.log"
        if not log_path.exists():
            raise FileNotFoundError(f"Log not found for run: {run_id}")
        return log_path.read_text()


class MemoryStorage:
    """In-memory storage backend for testing.

    Stores all data in dictionaries, no persistence.
    """

    def __init__(self) -> None:
        """Initialize empty storage."""
        self._artifacts: dict[str, dict[str, bytes]] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._logs: dict[str, str] = {}

    def save_artifact(
        self,
        run_id: str,
        filename: str,
        content: bytes | str,
    ) -> str:
        """Save an artifact to memory."""
        if run_id not in self._artifacts:
            self._artifacts[run_id] = {}

        if isinstance(content, str):
            content = content.encode()

        self._artifacts[run_id][filename] = content
        return f"memory://{run_id}/results/{filename}"

    def load_artifact(
        self,
        run_id: str,
        filename: str,
    ) -> bytes:
        """Load an artifact from memory."""
        if run_id not in self._artifacts:
            raise FileNotFoundError(f"Artifact not found: {filename}")
        if filename not in self._artifacts[run_id]:
            raise FileNotFoundError(f"Artifact not found: {filename}")
        return self._artifacts[run_id][filename]

    def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifacts for a run."""
        if run_id not in self._artifacts:
            return []
        return list(self._artifacts[run_id].keys())

    def save_manifest(
        self,
        run_id: str,
        manifest: dict[str, Any],
    ) -> str:
        """Save manifest to memory."""
        self._manifests[run_id] = manifest.copy()
        return f"memory://{run_id}/manifest.json"

    def load_manifest(self, run_id: str) -> dict[str, Any]:
        """Load manifest from memory."""
        if run_id not in self._manifests:
            raise FileNotFoundError(f"Manifest not found for run: {run_id}")
        return self._manifests[run_id].copy()

    def save_log(
        self,
        run_id: str,
        content: str,
        append: bool = False,
    ) -> str:
        """Save log to memory."""
        if append and run_id in self._logs:
            self._logs[run_id] += content
        else:
            self._logs[run_id] = content
        return f"memory://{run_id}/output.log"

    def load_log(self, run_id: str) -> str:
        """Load log from memory."""
        if run_id not in self._logs:
            raise FileNotFoundError(f"Log not found for run: {run_id}")
        return self._logs[run_id]

    def clear(self) -> None:
        """Clear all stored data."""
        self._artifacts.clear()
        self._manifests.clear()
        self._logs.clear()
