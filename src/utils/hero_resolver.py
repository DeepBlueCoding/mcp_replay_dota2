"""
Hero resolver using constants data from dotaconstants repository.
"""

from typing import Any, Dict, Optional

from src.resources.heroes_resources import heroes_resource


class HeroResolver:
    """Resolves hero IDs to hero data using dotaconstants."""

    def __init__(self):
        """Initialize the hero resolver with data from constants."""
        self._heroes_by_id = {}
        self._heroes_by_key = {}
        self._load_heroes()

    def _load_heroes(self):
        """Load hero data from constants."""
        # Get heroes from constants (legacy format)
        heroes_data = heroes_resource.get_all_heroes()

        if not heroes_data:
            raise RuntimeError("Heroes constants not available. Run scripts/fetch_constants.py first.")

        # Get raw constants for enriched data
        raw_constants = heroes_resource.get_heroes_constants_raw()

        # Build lookup dictionaries
        for hero_key, hero_info in heroes_data.items():
            hero_id = hero_info["hero_id"]

            # Get additional data from raw constants
            raw_hero = raw_constants.get(str(hero_id), {}) if raw_constants else {}

            # Add computed fields with real data from constants
            enriched_hero = {
                "hero_id": hero_id,
                "hero_key": hero_key,
                "canonical_name": hero_info["canonical_name"],
                "primary_attribute": hero_info["attribute"],
                "attack_type": raw_hero.get("attack_type", "Melee"),
                "roles": raw_hero.get("roles", ["Universal"]),
                "complexity": raw_hero.get("complexity", 1),
                "aliases": hero_info.get("aliases", [])
            }

            self._heroes_by_id[hero_id] = enriched_hero
            self._heroes_by_key[hero_key] = enriched_hero

    def resolve_hero_by_id(self, hero_id: int) -> Optional[Dict[str, Any]]:
        """
        Resolve hero by ID to enriched hero data.

        Args:
            hero_id: Dota 2 hero ID

        Returns:
            Dictionary with hero data or None if not found
        """
        hero_data = self._heroes_by_id.get(hero_id)
        if hero_data:
            return {
                "success": True,
                **hero_data
            }
        return None

    def resolve_hero_by_key(self, hero_key: str) -> Optional[Dict[str, Any]]:
        """
        Resolve hero by key to enriched hero data.

        Args:
            hero_key: Dota 2 hero key (e.g., "npc_dota_hero_pudge")

        Returns:
            Dictionary with hero data or None if not found
        """
        hero_data = self._heroes_by_key.get(hero_key)
        if hero_data:
            return {
                "success": True,
                **hero_data
            }
        return None

    def get_all_heroes(self) -> Dict[int, Dict[str, Any]]:
        """Get all heroes indexed by hero_id."""
        return self._heroes_by_id.copy()


# Global resolver instance
hero_resolver = HeroResolver()
