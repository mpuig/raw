"""Tests for agentic cache functionality."""

import json
import time
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, Mock, patch

import pytest

from raw_runtime import WorkflowContext, set_workflow_context
from raw_runtime.agentic import agentic
from raw_runtime.agentic_cache import AgenticCache


class TestAgenticCache:
    """Tests for AgenticCache class."""

    def setup_method(self) -> None:
        """Set up test cache directory."""
        self.cache_dir = Path("/tmp/test_agentic_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self) -> None:
        """Clean up test cache directory."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    def test_init_creates_directory(self) -> None:
        """Test that cache initialization creates directory."""
        cache_dir = self.cache_dir / "new_cache"
        cache = AgenticCache(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache.cache_dir == cache_dir
        assert cache.ttl_seconds == 604800  # 7 days default

    def test_init_with_custom_ttl(self) -> None:
        """Test cache initialization with custom TTL."""
        cache = AgenticCache(cache_dir=self.cache_dir, ttl_seconds=3600)
        assert cache.ttl_seconds == 3600

    def test_put_and_get_simple(self) -> None:
        """Test basic put and get operations."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        key = "test_key_123"
        cache.put(key, "test prompt", "test-model", "response_value", 0.01)

        result = cache.get(key)
        assert result == "response_value"

    def test_put_and_get_complex_response(self) -> None:
        """Test put and get with complex data structures."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        key = "test_key_complex"
        response_data = {
            "status": "ok",
            "items": [1, 2, 3],
            "nested": {"value": "test"},
        }
        cache.put(key, "prompt", "model", response_data, 0.02)

        result = cache.get(key)
        assert result == response_data

    def test_get_nonexistent_key(self) -> None:
        """Test getting a key that doesn't exist."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        result = cache.get("nonexistent_key")
        assert result is None

    def test_get_expired_entry(self) -> None:
        """Test that expired entries return None."""
        cache = AgenticCache(cache_dir=self.cache_dir, ttl_seconds=1)

        key = "test_key_expire"
        cache.put(key, "prompt", "model", "value", 0.01)

        # Wait for expiration
        time.sleep(1.1)

        result = cache.get(key)
        assert result is None

        # Cache file should be deleted
        cache_file = self.cache_dir / f"{key}.json"
        assert not cache_file.exists()

    def test_cache_file_structure(self) -> None:
        """Test that cache files have correct structure."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        key = "test_key_struct"
        cache.put(key, "test prompt", "claude-3-5-sonnet", "response", 0.05)

        cache_file = self.cache_dir / f"{key}.json"
        assert cache_file.exists()

        with open(cache_file) as f:
            data = json.load(f)

        assert "prompt" in data
        assert "model" in data
        assert "response" in data
        assert "timestamp" in data
        assert "cost" in data

        assert data["prompt"] == "test prompt"
        assert data["model"] == "claude-3-5-sonnet"
        assert data["response"] == "response"
        assert data["cost"] == 0.05
        assert isinstance(data["timestamp"], float)

    def test_corrupted_cache_file_handled(self) -> None:
        """Test that corrupted cache files are handled gracefully."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        key = "test_key_corrupt"
        cache_file = self.cache_dir / f"{key}.json"

        # Write corrupted JSON
        with open(cache_file, "w") as f:
            f.write("not valid json {{{")

        # Should return None and delete corrupted file
        result = cache.get(key)
        assert result is None
        assert not cache_file.exists()

    def test_clear_expired_removes_old_entries(self) -> None:
        """Test that clear_expired removes expired entries."""
        cache = AgenticCache(cache_dir=self.cache_dir, ttl_seconds=1)

        # Add some entries
        cache.put("key1", "prompt1", "model", "value1", 0.01)
        cache.put("key2", "prompt2", "model", "value2", 0.01)
        cache.put("key3", "prompt3", "model", "value3", 0.01)

        # Wait for expiration
        time.sleep(1.2)

        # Create a new cache instance to avoid same TTL
        cache2 = AgenticCache(cache_dir=self.cache_dir, ttl_seconds=1)

        # Add a new entry that won't expire
        cache2.put("key4", "prompt4", "model", "value4", 0.01)

        # Clear expired entries
        count = cache2.clear_expired()

        assert count == 3  # Three expired entries removed
        assert cache2.get("key4") == "value4"  # New entry still exists

    def test_clear_expired_with_corrupted_files(self) -> None:
        """Test that clear_expired removes corrupted files."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        # Create a corrupted file
        cache_file = self.cache_dir / "corrupt.json"
        with open(cache_file, "w") as f:
            f.write("invalid json")

        count = cache.clear_expired()
        assert count == 1
        assert not cache_file.exists()

    def test_stats_empty_cache(self) -> None:
        """Test stats on empty cache."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["cache_entries"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_with_hits_and_misses(self) -> None:
        """Test stats tracking hits and misses."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        # Add entry
        cache.put("key1", "prompt", "model", "value", 0.01)

        # Hit
        cache.get("key1")
        # Miss
        cache.get("key2")
        # Hit
        cache.get("key1")
        # Miss
        cache.get("key3")

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["total_requests"] == 4
        assert stats["hit_rate"] == 0.5
        assert stats["cache_entries"] == 1

    def test_stats_cache_size(self) -> None:
        """Test that stats correctly calculates cache size."""
        cache = AgenticCache(cache_dir=self.cache_dir)

        cache.put("key1", "prompt1", "model", "value1", 0.01)
        cache.put("key2", "prompt2", "model", "value2", 0.02)

        stats = cache.stats()
        assert stats["cache_entries"] == 2
        assert stats["total_size_bytes"] > 0

    def test_put_fails_gracefully(self) -> None:
        """Test that put failures don't raise exceptions."""
        # Create cache with invalid directory
        cache = AgenticCache(cache_dir=Path("/dev/null/invalid"))

        # Should not raise exception
        cache.put("key", "prompt", "model", "value", 0.01)


class TestAgenticCacheIntegration:
    """Integration tests for @agentic decorator with file-based cache."""

    def setup_method(self) -> None:
        """Set up test context and cache directory."""
        self.cache_dir = Path("/tmp/test_agentic_integration")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create .raw/cache/agentic directory in temp for testing
        self.raw_cache_dir = Path(".raw/cache/agentic")
        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)

        # Reset global cache
        import sys

        if "raw_runtime.agentic" in sys.modules:
            sys.modules["raw_runtime.agentic"]._cache = None  # type: ignore[attr-defined]

        self.ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context and cache directory."""
        import shutil
        import sys

        set_workflow_context(None)

        # Reset global cache
        if "raw_runtime.agentic" in sys.modules:
            sys.modules["raw_runtime.agentic"]._cache = None  # type: ignore[attr-defined]

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        if self.raw_cache_dir.exists():
            shutil.rmtree(self.raw_cache_dir)

    def test_file_cache_persistence_across_calls(self) -> None:
        """Test that cache persists across function calls."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process(text: str) -> str:
                pass

            # First call - miss
            result1 = process("test")
            assert result1 == "result"
            assert mock_client.messages.create.call_count == 1

            # Second call - hit from file cache
            result2 = process("test")
            assert result2 == "result"
            assert mock_client.messages.create.call_count == 1  # Not called again

            # Verify cache files exist in .raw/cache/agentic/
            cache_files = list(self.raw_cache_dir.glob("*.json"))
            assert len(cache_files) == 1

    def test_cache_ttl_parameter(self) -> None:
        """Test cache_ttl parameter in @agentic decorator."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
                cache_ttl=1,  # 1 second TTL
            )
            def process(text: str) -> str:
                pass

            # First call
            result1 = process("test")
            assert result1 == "result"
            assert mock_client.messages.create.call_count == 1

            # Second call immediately - should hit cache
            result2 = process("test")
            assert result2 == "result"
            assert mock_client.messages.create.call_count == 1

            # Wait for expiration
            time.sleep(1.1)

            # Third call - should miss cache
            result3 = process("test")
            assert result3 == "result"
            assert mock_client.messages.create.call_count == 2

    def test_cache_events_emitted(self) -> None:
        """Test that cache hit/miss events are emitted."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        events = []
        self.ctx.emit = lambda e: events.append(e)  # type: ignore[method-assign]

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process(text: str) -> str:
                pass

            # First call - should emit cache miss
            events.clear()
            result1 = process("test")
            assert result1 == "result"

            cache_miss_events = [e for e in events if e.event_type.value == "cache.miss"]
            assert len(cache_miss_events) == 1
            assert cache_miss_events[0].step_name == "process"

            # Second call - should emit cache hit
            events.clear()
            result2 = process("test")
            assert result2 == "result"

            cache_hit_events = [e for e in events if e.event_type.value == "cache.hit"]
            assert len(cache_hit_events) == 1
            assert cache_hit_events[0].step_name == "process"

    def test_context_cache_metrics(self) -> None:
        """Test that WorkflowContext tracks cache hits and misses."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process(text: str) -> str:
                pass

            # Initial metrics
            assert self.ctx.agentic_cache_hits == 0
            assert self.ctx.agentic_cache_misses == 0

            # First call - miss
            process("test1")
            assert self.ctx.agentic_cache_hits == 0
            assert self.ctx.agentic_cache_misses == 1

            # Second call with same input - hit
            process("test1")
            assert self.ctx.agentic_cache_hits == 1
            assert self.ctx.agentic_cache_misses == 1

            # Third call with different input - miss
            process("test2")
            assert self.ctx.agentic_cache_hits == 1
            assert self.ctx.agentic_cache_misses == 2

            # Fourth call with first input - hit
            process("test1")
            assert self.ctx.agentic_cache_hits == 2
            assert self.ctx.agentic_cache_misses == 2

    def test_cache_with_different_models(self) -> None:
        """Test that cache is model-specific."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process_haiku(text: str) -> str:
                pass

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-sonnet-20241022",
                cache=True,
            )
            def process_sonnet(text: str) -> str:
                pass

            # Same input, different models - both should miss cache
            process_haiku("test")
            assert mock_client.messages.create.call_count == 1

            process_sonnet("test")
            assert mock_client.messages.create.call_count == 2

            # Repeat calls should hit cache
            process_haiku("test")
            assert mock_client.messages.create.call_count == 2

            process_sonnet("test")
            assert mock_client.messages.create.call_count == 2

    def test_cache_with_typed_responses(self) -> None:
        """Test that cache works with various typed responses."""
        # Int response
        mock_response = Mock()
        mock_response.content = [Mock(text="42")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Count: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def count(text: str) -> int:
                pass

            result1 = count("test")
            assert result1 == 42
            assert isinstance(result1, int)

            result2 = count("test")
            assert result2 == 42
            assert isinstance(result2, int)
            assert mock_client.messages.create.call_count == 1

    def test_cache_disabled(self) -> None:
        """Test that cache=False disables caching."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def process(text: str) -> str:
                pass

            # Multiple calls should all hit API
            process("test")
            process("test")
            process("test")

            assert mock_client.messages.create.call_count == 3

            # No cache metrics
            assert self.ctx.agentic_cache_hits == 0
            assert self.ctx.agentic_cache_misses == 0

    def test_cache_files_readable(self) -> None:
        """Test that cache files are human-readable JSON."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process(text: str) -> str:
                pass

            process("test input")

            # Find cache file in .raw/cache/agentic/
            cache_files = list(self.raw_cache_dir.glob("*.json"))
            assert len(cache_files) == 1

            # Read and verify format
            with open(cache_files[0]) as f:
                data = json.load(f)

            assert data["prompt"] == "Process: test input"
            assert data["model"] == "claude-3-5-haiku-20241022"
            assert data["response"] == "result"
            assert data["cost"] > 0
            assert isinstance(data["timestamp"], float)
