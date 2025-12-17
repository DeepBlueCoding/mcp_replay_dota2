"""
Game context model for version-aware replay analysis.

Encapsulates version-specific data that services need to analyze replays correctly.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from src.models.map_data import MapData
    from src.services.models.replay_data import ParsedReplayData


@dataclass
class GameContext:
    """
    Version-specific context for replay analysis.

    Services receive this context to access version-appropriate map data,
    neutral item tiers, and other patch-specific information.
    """

    match_id: int
    build_num: int
    patch_version: str

    # Lazily loaded version-specific data
    _map_data: Optional["MapData"] = field(default=None, repr=False)
    _neutral_item_tiers: Optional[Dict[str, int]] = field(default=None, repr=False)

    @property
    def map_data(self) -> "MapData":
        """
        Get map data for this patch version.

        Lazily loads from versioned map resources.
        """
        if self._map_data is None:
            from src.resources.versioned_map_resources import get_versioned_map_data

            provider = get_versioned_map_data()
            self._map_data = provider.get_map_data(self.patch_version)
        return self._map_data

    @property
    def neutral_item_tiers(self) -> Dict[str, int]:
        """
        Get neutral item tier mapping for this patch version.

        Returns dict mapping item internal names to tier numbers (1-5).
        """
        if self._neutral_item_tiers is None:
            from src.utils.versioned_constants import get_versioned_constants

            constants = get_versioned_constants()
            self._neutral_item_tiers = constants.get_all_neutral_item_tiers(
                self.patch_version
            )
        return self._neutral_item_tiers

    def get_neutral_item_tier(self, item_name: str) -> Optional[int]:
        """
        Get tier for a specific neutral item.

        Args:
            item_name: Internal item name (e.g., "trusty_shovel")

        Returns:
            Tier number (1-5) or None if not a neutral item
        """
        return self.neutral_item_tiers.get(item_name)

    @classmethod
    def from_parsed_data(cls, data: "ParsedReplayData") -> "GameContext":
        """
        Create context from parsed replay data.

        Extracts build_num from header and resolves patch version.

        Args:
            data: Parsed replay data with header info

        Returns:
            GameContext with resolved patch version
        """
        from src.utils.version_resolver import get_version_resolver

        resolver = get_version_resolver()

        build_num = 0
        if data.header:
            build_num = data.header.build_num

        patch_version = resolver.get_patch_version(build_num)

        return cls(
            match_id=data.match_id,
            build_num=build_num,
            patch_version=patch_version,
        )

    @classmethod
    def for_version(cls, patch_version: str, match_id: int = 0) -> "GameContext":
        """
        Create context for a specific patch version.

        Useful for testing or when replay header is unavailable.

        Args:
            patch_version: Patch version string (e.g., "7.39")
            match_id: Optional match ID

        Returns:
            GameContext for the specified version
        """
        return cls(
            match_id=match_id,
            build_num=0,
            patch_version=patch_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (without lazy-loaded data)."""
        return {
            "match_id": self.match_id,
            "build_num": self.build_num,
            "patch_version": self.patch_version,
        }
