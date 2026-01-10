"""File-based caching for @agentic decorator with TTL and metrics."""

import json
import time
from pathlib import Path
from typing import Any


class AgenticCache:
    """Persistent file-based cache for agentic step responses."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 604800) -> None:
        """Initialize cache with directory and TTL.

        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live for cache entries (default: 7 days)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

        # Create cache directory if it doesn't exist
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, NotADirectoryError):
            # Directory creation failed - cache will be non-functional but won't crash
            pass

    def get(self, key: str) -> Any | None:
        """Get cached response, None if miss or expired.

        Args:
            key: Cache key (SHA256 hash)

        Returns:
            Cached response or None if miss/expired
        """
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            with open(cache_file) as f:
                entry = json.load(f)

            # Check TTL expiration
            timestamp = entry.get("timestamp", 0)
            if time.time() - timestamp > self.ttl_seconds:
                # Entry expired - remove it
                cache_file.unlink(missing_ok=True)
                self._misses += 1
                return None

            self._hits += 1
            return entry.get("response")

        except (json.JSONDecodeError, KeyError, OSError):
            # Corrupted cache file - remove it and treat as miss
            cache_file.unlink(missing_ok=True)
            self._misses += 1
            return None

    def put(self, key: str, prompt: str, model: str, response: Any, cost: float) -> None:
        """Store response in cache.

        Args:
            key: Cache key (SHA256 hash)
            prompt: Original prompt
            model: Model used
            response: Response to cache
            cost: Cost of the API call
        """
        cache_file = self.cache_dir / f"{key}.json"

        entry = {
            "prompt": prompt,
            "model": model,
            "response": response,
            "timestamp": time.time(),
            "cost": cost,
        }

        try:
            with open(cache_file, "w") as f:
                json.dump(entry, f, indent=2)
        except (OSError, TypeError):
            # Silently fail if we can't write cache
            pass

    def clear_expired(self) -> int:
        """Remove expired entries, return count.

        Returns:
            Number of expired entries removed
        """
        count = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    entry = json.load(f)

                timestamp = entry.get("timestamp", 0)
                if current_time - timestamp > self.ttl_seconds:
                    cache_file.unlink()
                    count += 1

            except (json.JSONDecodeError, KeyError, OSError):
                # Corrupted file - remove it
                cache_file.unlink(missing_ok=True)
                count += 1

        return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        Returns:
            Dictionary with hits, misses, size, hit_rate
        """
        # Count cache files
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files if f.exists())

        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_entries": len(cache_files),
            "total_size_bytes": total_size,
        }
