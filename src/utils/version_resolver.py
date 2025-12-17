"""
Patch version resolver for Dota 2 replays.

Maps replay build_num (from HeaderInfo) to patch version string.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PatchInfo:
    """Information about a Dota 2 patch."""

    version: str
    min_build: int
    max_build: int
    date: str
    name: Optional[str] = None
    notes: Optional[str] = None


class PatchVersionResolver:
    """
    Resolves replay build_num to patch version.

    Build numbers increase monotonically with game updates.
    Uses build_ranges.json to map build numbers to patch versions.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the version resolver.

        Args:
            data_dir: Directory containing versions data. Defaults to project data/versions
        """
        if data_dir:
            self._data_dir = data_dir
        else:
            project_root = Path(__file__).parent.parent.parent
            self._data_dir = project_root / "data" / "versions"

        self._patches: Dict[str, PatchInfo] = {}
        self._fallback_version = "7.39"
        self._oldest_supported = "7.33"
        self._highest_known_build = 0

        self._load_build_ranges()

    def _load_build_ranges(self) -> None:
        """Load build ranges from JSON file."""
        build_file = self._data_dir / "build_ranges.json"

        if not build_file.exists():
            logger.warning(f"Build ranges file not found: {build_file}")
            return

        try:
            data = json.loads(build_file.read_text())
            self._fallback_version = data.get("fallback_version", "7.39")
            self._oldest_supported = data.get("oldest_supported", "7.33")

            for version, info in data.get("patches", {}).items():
                self._patches[version] = PatchInfo(
                    version=version,
                    min_build=info["min_build"],
                    max_build=info["max_build"],
                    date=info["date"],
                    name=info.get("name"),
                    notes=info.get("notes"),
                )
                if info["max_build"] > self._highest_known_build:
                    self._highest_known_build = info["max_build"]

            logger.info(
                f"Loaded {len(self._patches)} patch versions, "
                f"highest known build: {self._highest_known_build}"
            )

        except Exception as e:
            logger.error(f"Failed to load build ranges: {e}")

    def get_patch_version(self, build_num: int) -> str:
        """
        Get patch version string for a build number.

        Args:
            build_num: Game build number from replay HeaderInfo

        Returns:
            Patch version string (e.g., "7.39")
        """
        if build_num <= 0:
            logger.warning(f"Invalid build number: {build_num}, using fallback")
            return self._fallback_version

        # Check explicit mappings
        for version, info in self._patches.items():
            if info.min_build <= build_num < info.max_build:
                return version

        # Heuristic: if higher than all known, assume latest
        if build_num >= self._highest_known_build:
            logger.info(
                f"Build {build_num} >= {self._highest_known_build}, "
                f"assuming {self._fallback_version}"
            )
            return self._fallback_version

        # Lower than all known = very old replay
        logger.warning(
            f"Build {build_num} older than known patches, "
            f"using {self._oldest_supported}"
        )
        return self._oldest_supported

    def get_patch_info(self, version: str) -> Optional[PatchInfo]:
        """
        Get detailed info about a patch version.

        Args:
            version: Patch version string (e.g., "7.39")

        Returns:
            PatchInfo or None if not found
        """
        return self._patches.get(version)

    def is_known_version(self, build_num: int) -> bool:
        """
        Check if this build number maps to a known patch.

        Args:
            build_num: Game build number

        Returns:
            True if the build maps to an explicitly defined patch
        """
        for info in self._patches.values():
            if info.min_build <= build_num < info.max_build:
                return True
        return False

    def get_all_versions(self) -> Dict[str, PatchInfo]:
        """Get all known patch versions."""
        return self._patches.copy()

    @property
    def fallback_version(self) -> str:
        """Get the fallback version for unknown builds."""
        return self._fallback_version

    @property
    def oldest_supported(self) -> str:
        """Get the oldest supported patch version."""
        return self._oldest_supported


# Singleton instance
_resolver: Optional[PatchVersionResolver] = None


def get_version_resolver() -> PatchVersionResolver:
    """Get the singleton version resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = PatchVersionResolver()
    return _resolver
