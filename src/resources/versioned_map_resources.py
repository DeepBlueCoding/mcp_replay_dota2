"""
Versioned map data resource for Dota 2.

Loads map data for specific patch versions, falling back to latest known version
when patch-specific data is unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from src.models.map_data import MapData

logger = logging.getLogger(__name__)


class VersionedMapData:
    """
    Loads map data for specific patch versions.

    Falls back to latest known version for unknown patches.
    Map data is cached in memory after first load.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the versioned map data provider.

        Args:
            data_dir: Directory containing versions/patches/. Defaults to project data/
        """
        if data_dir:
            self._data_dir = data_dir
        else:
            project_root = Path(__file__).parent.parent.parent
            self._data_dir = project_root / "data"

        self._patches_dir = self._data_dir / "versions" / "patches"
        self._cache: Dict[str, MapData] = {}
        self._fallback_version = "7.39"

    def get_map_data(self, patch_version: str) -> MapData:
        """
        Get map data for a specific patch.

        Args:
            patch_version: Patch version string (e.g., "7.39")

        Returns:
            MapData for the patch (or fallback if not found)
        """
        if patch_version in self._cache:
            return self._cache[patch_version]

        map_data = self._load_map_data(patch_version)
        self._cache[patch_version] = map_data
        return map_data

    def _load_map_data(self, patch_version: str) -> MapData:
        """
        Load map data from JSON file.

        Falls back to:
        1. Fallback version if patch-specific not found
        2. Hardcoded map data if no JSON files exist
        """
        map_file = self._patches_dir / patch_version / "map_data.json"

        if not map_file.exists():
            # Try fallback version
            fallback_file = self._patches_dir / self._fallback_version / "map_data.json"

            if fallback_file.exists():
                logger.warning(
                    f"No map data for {patch_version}, using {self._fallback_version}"
                )
                map_file = fallback_file
            else:
                # Fall back to hardcoded data
                logger.warning(
                    "No versioned map data found, using hardcoded defaults"
                )
                from src.resources.map_resources import get_map_data
                return get_map_data()

        try:
            data = json.loads(map_file.read_text())
            map_data = MapData.model_validate(data)
            logger.info(f"Loaded map data for patch {patch_version}")
            return map_data
        except Exception as e:
            logger.error(f"Failed to load map data from {map_file}: {e}")
            # Fall back to hardcoded data
            from src.resources.map_resources import get_map_data
            return get_map_data()

    def get_available_versions(self) -> list[str]:
        """Get list of patch versions with available map data."""
        versions = []
        if self._patches_dir.exists():
            for patch_dir in self._patches_dir.iterdir():
                if patch_dir.is_dir():
                    map_file = patch_dir / "map_data.json"
                    if map_file.exists():
                        versions.append(patch_dir.name)
        return sorted(versions)

    def clear_cache(self) -> None:
        """Clear the map data cache."""
        self._cache.clear()


# Singleton instance
_versioned_map_data: Optional[VersionedMapData] = None


def get_versioned_map_data() -> VersionedMapData:
    """Get the singleton versioned map data instance."""
    global _versioned_map_data
    if _versioned_map_data is None:
        _versioned_map_data = VersionedMapData()
    return _versioned_map_data
