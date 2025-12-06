"""Tests for storage backend abstraction."""

import json

import pytest

from raw_runtime.storage import (
    FileSystemStorage,
    MemoryStorage,
    StorageBackend,
    get_storage,
    serialize_for_storage,
    set_storage,
)


class TestStorageBackendProtocol:
    """Test that implementations satisfy the StorageBackend protocol."""

    def test_filesystem_storage_is_storage_backend(self):
        assert isinstance(FileSystemStorage(), StorageBackend)

    def test_memory_storage_is_storage_backend(self):
        assert isinstance(MemoryStorage(), StorageBackend)


class TestFileSystemStorage:
    """Tests for FileSystemStorage implementation."""

    @pytest.fixture
    def storage(self, tmp_path):
        return FileSystemStorage(base_dir=tmp_path)

    def test_save_and_load_artifact_text(self, storage):
        storage.save_artifact("run-123", "output.txt", "Hello, World!")
        content = storage.load_artifact("run-123", "output.txt")
        assert content == b"Hello, World!"

    def test_save_and_load_artifact_bytes(self, storage):
        data = b"\x00\x01\x02\x03"
        storage.save_artifact("run-123", "binary.bin", data)
        content = storage.load_artifact("run-123", "binary.bin")
        assert content == data

    def test_load_artifact_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_artifact("run-123", "missing.txt")

    def test_list_artifacts_empty(self, storage):
        assert storage.list_artifacts("run-123") == []

    def test_list_artifacts(self, storage):
        storage.save_artifact("run-123", "a.txt", "a")
        storage.save_artifact("run-123", "b.txt", "b")
        storage.save_artifact("run-123", "c.json", "{}")

        artifacts = storage.list_artifacts("run-123")
        assert set(artifacts) == {"a.txt", "b.txt", "c.json"}

    def test_save_and_load_manifest(self, storage):
        manifest = {
            "schema_version": "1.0.0",
            "workflow": {"id": "test"},
            "steps": [],
        }
        storage.save_manifest("run-123", manifest)
        loaded = storage.load_manifest("run-123")
        assert loaded == manifest

    def test_load_manifest_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_manifest("run-123")

    def test_save_and_load_log(self, storage):
        storage.save_log("run-123", "Line 1\n")
        content = storage.load_log("run-123")
        assert content == "Line 1\n"

    def test_save_log_append(self, storage):
        storage.save_log("run-123", "Line 1\n")
        storage.save_log("run-123", "Line 2\n", append=True)
        content = storage.load_log("run-123")
        assert content == "Line 1\nLine 2\n"

    def test_load_log_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_log("run-123")

    def test_directory_structure(self, storage, tmp_path):
        storage.save_artifact("run-123", "report.json", "{}")
        storage.save_manifest("run-123", {"test": True})
        storage.save_log("run-123", "log content")

        assert (tmp_path / "run-123" / "results" / "report.json").exists()
        assert (tmp_path / "run-123" / "manifest.json").exists()
        assert (tmp_path / "run-123" / "output.log").exists()

    def test_returns_path_strings(self, storage):
        path = storage.save_artifact("run-123", "test.txt", "data")
        assert "run-123" in path
        assert "results" in path
        assert "test.txt" in path


class TestMemoryStorage:
    """Tests for MemoryStorage implementation."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    def test_save_and_load_artifact_text(self, storage):
        storage.save_artifact("run-123", "output.txt", "Hello, World!")
        content = storage.load_artifact("run-123", "output.txt")
        assert content == b"Hello, World!"

    def test_save_and_load_artifact_bytes(self, storage):
        data = b"\x00\x01\x02\x03"
        storage.save_artifact("run-123", "binary.bin", data)
        content = storage.load_artifact("run-123", "binary.bin")
        assert content == data

    def test_load_artifact_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_artifact("run-123", "missing.txt")

    def test_list_artifacts(self, storage):
        storage.save_artifact("run-123", "a.txt", "a")
        storage.save_artifact("run-123", "b.txt", "b")
        assert set(storage.list_artifacts("run-123")) == {"a.txt", "b.txt"}

    def test_save_and_load_manifest(self, storage):
        manifest = {"test": True, "steps": [1, 2, 3]}
        storage.save_manifest("run-123", manifest)
        loaded = storage.load_manifest("run-123")
        assert loaded == manifest

    def test_load_manifest_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_manifest("run-123")

    def test_save_and_load_log(self, storage):
        storage.save_log("run-123", "Line 1\n")
        assert storage.load_log("run-123") == "Line 1\n"

    def test_save_log_append(self, storage):
        storage.save_log("run-123", "Line 1\n")
        storage.save_log("run-123", "Line 2\n", append=True)
        assert storage.load_log("run-123") == "Line 1\nLine 2\n"

    def test_load_log_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_log("run-123")

    def test_returns_memory_urls(self, storage):
        path = storage.save_artifact("run-123", "test.txt", "data")
        assert path == "memory://run-123/results/test.txt"

    def test_isolation_between_runs(self, storage):
        storage.save_artifact("run-1", "data.txt", "run 1 data")
        storage.save_artifact("run-2", "data.txt", "run 2 data")

        assert storage.load_artifact("run-1", "data.txt") == b"run 1 data"
        assert storage.load_artifact("run-2", "data.txt") == b"run 2 data"


class TestGlobalStorage:
    """Tests for global storage getter/setter."""

    def test_get_storage_returns_filesystem_by_default(self):
        set_storage(None)
        storage = get_storage()
        assert isinstance(storage, FileSystemStorage)

    def test_set_and_get_storage(self):
        memory = MemoryStorage()
        set_storage(memory)
        assert get_storage() is memory
        set_storage(None)


class TestSerializeForStorage:
    """Tests for serialize_for_storage helper."""

    def test_serialize_dict(self):
        data = {"key": "value", "number": 42}
        result = serialize_for_storage(data)
        assert json.loads(result) == data

    def test_serialize_list(self):
        data = [1, 2, 3]
        result = serialize_for_storage(data)
        assert json.loads(result) == data

    def test_serialize_string(self):
        result = serialize_for_storage("hello")
        assert result == "hello"

    def test_serialize_number(self):
        result = serialize_for_storage(42)
        assert result == "42"

    def test_serialize_bytes_raises(self):
        with pytest.raises(ValueError, match="bytes directly"):
            serialize_for_storage(b"binary data")
