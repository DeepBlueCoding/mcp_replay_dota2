"""
Versioned game constants for Dota 2.

Manages version-specific constants like neutral item tiers that change between patches.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VersionedConstants:
    """
    Manages version-specific game constants.

    Currently handles:
    - Neutral item tiers (change between patches)

    Falls back to dotaconstants items.json when patch-specific data unavailable.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the versioned constants provider.

        Args:
            data_dir: Directory containing data/. Defaults to project data/
        """
        if data_dir:
            self._data_dir = data_dir
        else:
            project_root = Path(__file__).parent.parent.parent
            self._data_dir = project_root / "data"

        self._patches_dir = self._data_dir / "versions" / "patches"
        self._constants_dir = self._data_dir / "constants"
        self._cache: Dict[str, Dict[str, int]] = {}
        self._fallback_version = "7.39"

    def get_neutral_item_tier(
        self, item_name: str, patch_version: str
    ) -> Optional[int]:
        """
        Get tier for a specific neutral item in a patch.

        Args:
            item_name: Internal item name (e.g., "trusty_shovel")
            patch_version: Patch version string (e.g., "7.39")

        Returns:
            Tier number (1-5) or None if not a neutral item
        """
        tiers = self.get_all_neutral_item_tiers(patch_version)
        return tiers.get(item_name)

    def get_all_neutral_item_tiers(self, patch_version: str) -> Dict[str, int]:
        """
        Get all neutral item tiers for a patch.

        Args:
            patch_version: Patch version string (e.g., "7.39")

        Returns:
            Dict mapping item internal names to tier numbers
        """
        if patch_version in self._cache:
            return self._cache[patch_version]

        tiers = self._load_neutral_item_tiers(patch_version)
        self._cache[patch_version] = tiers
        return tiers

    def _load_neutral_item_tiers(self, patch_version: str) -> Dict[str, int]:
        """
        Load neutral item tiers from patch-specific JSON or fallback.

        Falls back to:
        1. Fallback version if patch-specific not found
        2. dotaconstants items.json if no patch data exists
        """
        items_file = self._patches_dir / patch_version / "neutral_items.json"

        if not items_file.exists():
            # Try fallback version
            fallback_file = (
                self._patches_dir / self._fallback_version / "neutral_items.json"
            )

            if fallback_file.exists():
                logger.warning(
                    f"No neutral items for {patch_version}, using {self._fallback_version}"
                )
                items_file = fallback_file
            else:
                # Fall back to dotaconstants
                logger.warning(
                    "No versioned neutral items found, using dotaconstants"
                )
                return self._load_from_dotaconstants()

        try:
            data = json.loads(items_file.read_text())
            tiers = {}
            for item_name, item_data in data.get("items", {}).items():
                if item_data.get("status") != "removed":
                    tier = item_data.get("tier")
                    if tier is not None:
                        tiers[item_name] = tier

            logger.info(
                f"Loaded {len(tiers)} neutral item tiers for patch {patch_version}"
            )
            return tiers
        except Exception as e:
            logger.error(f"Failed to load neutral items from {items_file}: {e}")
            return self._load_from_dotaconstants()

    def _load_from_dotaconstants(self) -> Dict[str, int]:
        """Load neutral item tiers from dotaconstants items.json."""
        items_file = self._constants_dir / "items.json"

        if not items_file.exists():
            logger.error("dotaconstants items.json not found")
            return {}

        try:
            data = json.loads(items_file.read_text())
            tiers = {}
            for item_name, item_data in data.items():
                tier = item_data.get("tier")
                if tier is not None:
                    tiers[item_name] = tier

            logger.info(f"Loaded {len(tiers)} neutral items from dotaconstants")
            return tiers
        except Exception as e:
            logger.error(f"Failed to load dotaconstants items.json: {e}")
            return {}

    def get_neutral_items_by_tier(
        self, tier: int, patch_version: str
    ) -> List[str]:
        """
        Get all neutral items of a specific tier for a patch.

        Args:
            tier: Tier number (1-5)
            patch_version: Patch version string

        Returns:
            List of item internal names
        """
        tiers = self.get_all_neutral_item_tiers(patch_version)
        return [name for name, t in tiers.items() if t == tier]

    def is_neutral_item(self, item_name: str, patch_version: str) -> bool:
        """
        Check if an item is a neutral item in a specific patch.

        Args:
            item_name: Internal item name
            patch_version: Patch version string

        Returns:
            True if the item is a neutral item
        """
        return item_name in self.get_all_neutral_item_tiers(patch_version)

    def clear_cache(self) -> None:
        """Clear the neutral items cache."""
        self._cache.clear()


# Singleton instance
_versioned_constants: Optional[VersionedConstants] = None


def get_versioned_constants() -> VersionedConstants:
    """Get the singleton versioned constants instance."""
    global _versioned_constants
    if _versioned_constants is None:
        _versioned_constants = VersionedConstants()
    return _versioned_constants
