"""
Replay data cache using diskcache.

Stores ParsedReplayData from python-manta v2 single-pass parsing.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from diskcache import Cache

from ..models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "mcp_dota2" / "parsed_replays_v2"
DEFAULT_TTL = 86400 * 7  # 7 days
DEFAULT_SIZE_LIMIT = 5 * 1024**3  # 5GB


class ReplayCache:
    """
    Disk-based cache for parsed replay data.

    Uses diskcache for persistent storage with LRU eviction.
    NO MCP DEPENDENCIES - can be used from any interface.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        size_limit: int = DEFAULT_SIZE_LIMIT,
        ttl: int = DEFAULT_TTL,
    ):
        """Initialize the cache.

        Args:
            cache_dir: Directory for cache storage. Defaults to ~/.cache/mcp_dota2/parsed_replays_v2
            size_limit: Maximum cache size in bytes. Defaults to 5GB.
            ttl: Time-to-live in seconds. Defaults to 7 days.
        """
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(
            directory=str(self._cache_dir),
            size_limit=size_limit,
        )
        self._ttl = ttl

    def get(self, match_id: int) -> Optional[ParsedReplayData]:
        """Get cached data for a match.

        Args:
            match_id: The match ID

        Returns:
            ParsedReplayData if cached, None otherwise
        """
        cache_key = f"replay_v2_{match_id}"
        cached = self._cache.get(cache_key)

        if cached is not None:
            logger.debug(f"Cache hit for match {match_id}")
            # LRU behavior: reset TTL on access
            self._cache.touch(cache_key, expire=self._ttl)
            return ParsedReplayData.from_cache_dict(cached)

        logger.debug(f"Cache miss for match {match_id}")
        return None

    def set(self, match_id: int, data: ParsedReplayData) -> None:
        """Store parsed data in cache.

        Args:
            match_id: The match ID
            data: Parsed replay data to cache
        """
        cache_key = f"replay_v2_{match_id}"
        self._cache.set(cache_key, data.to_cache_dict(), expire=self._ttl)
        logger.info(f"Cached parsed data for match {match_id}")

    def has(self, match_id: int) -> bool:
        """Check if match data is cached.

        Args:
            match_id: The match ID

        Returns:
            True if cached, False otherwise
        """
        cache_key = f"replay_v2_{match_id}"
        return cache_key in self._cache

    def delete(self, match_id: int) -> bool:
        """Remove cached data for a match.

        Args:
            match_id: The match ID

        Returns:
            True if deleted, False if not found
        """
        cache_key = f"replay_v2_{match_id}"
        return self._cache.delete(cache_key)

    def clear_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        return self._cache.expire()

    def clear_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "size_bytes": self._cache.volume(),
            "count": len(self._cache),
            "directory": str(self._cache_dir),
            "ttl_seconds": self._ttl,
        }
