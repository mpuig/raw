"""Composition root for runtime dependency injection.

Centralizes the creation and wiring of runtime components.
This is the single place where concrete implementations are bound to protocols,
following the Composition Root pattern from clean architecture.

Usage:
    # Default usage (production)
    storage = RuntimeContainer.storage()
    telemetry = RuntimeContainer.telemetry()

    # Testing with mocks
    RuntimeContainer.set_storage(MockStorage())
    RuntimeContainer.set_telemetry(MockTelemetry())

    # Reset to defaults
    RuntimeContainer.reset()
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from raw_runtime.drivers.orchestrator import HttpOrchestrator, LocalOrchestrator
from raw_runtime.drivers.secrets import (
    ChainedSecretProvider,
    DotEnvSecretProvider,
    EnvVarSecretProvider,
)
from raw_runtime.drivers.storage import FileSystemStorage
from raw_runtime.drivers.telemetry import NullSink
from raw_runtime.protocols.orchestrator import Orchestrator
from raw_runtime.protocols.secrets import SecretProvider
from raw_runtime.protocols.storage import StorageBackend
from raw_runtime.protocols.telemetry import TelemetrySink

if TYPE_CHECKING:
    from raw_runtime.manifest import ManifestWriter


class RuntimeContainer:
    """Service container for runtime dependencies.

    Provides lazy initialization of default implementations and
    allows overriding for testing purposes.

    Components:
    - telemetry: Observability (metrics, events)
    - storage: Artifact persistence
    - secrets: Credential management
    - orchestrator: Workflow triggering
    - manifest_writer: Manifest persistence
    """

    _telemetry: TelemetrySink | None = None
    _storage: StorageBackend | None = None
    _secrets: SecretProvider | None = None
    _orchestrator: Orchestrator | None = None
    # Note: _manifest_writer managed by manifest module to avoid circular imports

    # Telemetry

    @classmethod
    def telemetry(cls) -> TelemetrySink:
        """Get the telemetry sink.

        Returns NullSink by default (telemetry is opt-in).
        """
        if cls._telemetry is None:
            cls._telemetry = NullSink()
        return cls._telemetry

    @classmethod
    def set_telemetry(cls, sink: TelemetrySink | None) -> None:
        """Override the telemetry sink."""
        cls._telemetry = sink

    # Storage

    @classmethod
    def storage(cls) -> StorageBackend:
        """Get the storage backend.

        Returns FileSystemStorage by default.
        """
        if cls._storage is None:
            cls._storage = FileSystemStorage()
        return cls._storage

    @classmethod
    def set_storage(cls, storage: StorageBackend | None) -> None:
        """Override the storage backend."""
        cls._storage = storage

    # Secrets

    @classmethod
    def secrets(cls) -> SecretProvider:
        """Get the secret provider.

        Returns ChainedSecretProvider (env + dotenv) by default.
        """
        if cls._secrets is None:
            cls._secrets = ChainedSecretProvider([
                EnvVarSecretProvider(),
                DotEnvSecretProvider(),
            ])
        return cls._secrets

    @classmethod
    def set_secrets(cls, provider: SecretProvider | None) -> None:
        """Override the secret provider."""
        cls._secrets = provider

    # Orchestrator

    @classmethod
    def orchestrator(cls, workflows_dir: Path | None = None) -> Orchestrator:
        """Get the orchestrator.

        Returns HttpOrchestrator if RAW_SERVER_URL is set,
        otherwise LocalOrchestrator.
        """
        if cls._orchestrator is None:
            server_url = os.environ.get("RAW_SERVER_URL")
            if server_url:
                cls._orchestrator = HttpOrchestrator(server_url)
            else:
                cls._orchestrator = LocalOrchestrator(workflows_dir)
        return cls._orchestrator

    @classmethod
    def set_orchestrator(cls, orchestrator: Orchestrator | None) -> None:
        """Override the orchestrator."""
        cls._orchestrator = orchestrator

    # Manifest Writer
    # Note: Delegates to manifest module to avoid circular imports

    @classmethod
    def manifest_writer(cls) -> "ManifestWriter":
        """Get the manifest writer.

        Returns LocalManifestWriter by default.
        Delegates to manifest module to avoid circular imports.
        """
        from raw_runtime.manifest import get_manifest_writer

        return get_manifest_writer()

    @classmethod
    def set_manifest_writer(cls, writer: "ManifestWriter | None") -> None:
        """Override the manifest writer."""
        from raw_runtime.manifest import set_manifest_writer

        set_manifest_writer(writer)

    # Reset

    @classmethod
    def reset(cls) -> None:
        """Reset all overrides to defaults.

        Call this in test teardown to ensure clean state.
        """
        cls._telemetry = None
        cls._storage = None
        cls._secrets = None
        cls._orchestrator = None
        # Reset manifest writer via its module
        from raw_runtime.manifest import set_manifest_writer

        set_manifest_writer(None)
