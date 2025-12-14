"""Storage capability - File storage operations.

Supports S3, GCS, Azure Blob, and local filesystem.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class StorageCapability(Capability):
    """File storage capability.

    Usage:
        # Upload a file
        result = await self.capability("storage").call(
            action="upload",
            bucket="my-bucket",
            key="reports/2024/report.pdf",
            file_path="/tmp/report.pdf",
        )

        # Download a file
        result = await self.capability("storage").call(
            action="download",
            bucket="my-bucket",
            key="reports/2024/report.pdf",
            destination="/tmp/downloaded.pdf",
        )
    """

    name: ClassVar[str] = "storage"
    description: ClassVar[str] = "File storage operations (S3, GCS, local)"
    triggers: ClassVar[list[str]] = ["storage.object.created", "storage.object.deleted"]

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Perform storage operations.

        Args:
            action: Operation ("upload", "download", "delete", "list")
            bucket: Bucket or container name
            key: Object key/path
            file_path: Local file path (for upload)
            destination: Local destination path (for download)
            provider: Provider ("s3", "gcs", "azure", "local") - default "s3"

        Yields:
            CapabilityEvent with types: started, progress, completed, failed
        """
        raise NotImplementedError(
            "Storage capability not implemented. "
            "Configure cloud storage credentials to use this capability."
        )
        yield
