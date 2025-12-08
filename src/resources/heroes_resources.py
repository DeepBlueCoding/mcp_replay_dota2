import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from python_manta import Hero

from src.models.hero_counters import HeroCounters, HeroCountersDatabase
from src.utils.constants_fetcher import constants_fetcher
from src.utils.match_fetcher import MatchFetcher
from src.utils.pro_scene_fetcher import pro_scene_fetcher
from src.utils.replay_downloader import ReplayDownloader

logger = logging.getLogger(__name__)


class HeroesResource:
    """Resource class for managing Dota 2 hero data using dotaconstants."""

    def __init__(self):
        """Initialize the heroes resource."""
        self.replay_downloader = ReplayDownloader()
        self.constants = constants_fetcher
        self.match_fetcher = MatchFetcher()
        self._hero_counters: Optional[HeroCountersDatabase] = None

    def _load_hero_counters(self) -> Optional[HeroCountersDatabase]:
        """Load hero counters database from JSON file."""
        if self._hero_counters is not None:
            return self._hero_counters

        counters_path = Path(__file__).parent.parent.parent / "data" / "constants" / "hero_counters.json"
        if not counters_path.exists():
            logger.warning(f"Hero counters file not found: {counters_path}")
            return None

        with open(counters_path) as f:
            data = json.load(f)
            self._hero_counters = HeroCountersDatabase(**data)

        return self._hero_counters

    def get_hero_counters(self, hero_id: int) -> Optional[HeroCounters]:
        """Get counter picks data for a specific hero."""
        counters_db = self._load_hero_counters()
        if not counters_db:
            return None
        return counters_db.heroes.get(str(hero_id))

    def get_all_hero_counters(self) -> Dict[str, HeroCounters]:
        """Get all hero counter picks data."""
        counters_db = self._load_hero_counters()
        if not counters_db:
            return {}
        return counters_db.heroes

    def _convert_constants_to_legacy_format(
        self, heroes_constants: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Convert dotaconstants hero format to our legacy format for compatibility.

        Args:
            heroes_constants: Raw heroes data from dotaconstants

        Returns:
            Heroes data in legacy format with npc_ keys, including counter picks
        """
        legacy_heroes = {}
        counters_db = self._load_hero_counters()

        for hero_id, hero_data in heroes_constants.items():
            hero_key = hero_data.get("name", f"npc_dota_hero_{hero_id}")

            legacy_hero = {
                "hero_id": int(hero_id),
                "canonical_name": hero_data.get("localized_name", "Unknown"),
                "attribute": self._map_attribute(hero_data.get("primary_attr", "str")),
                "aliases": self._generate_aliases(hero_data),
                "counters": [],
                "good_against": [],
                "when_to_pick": []
            }

            if counters_db and hero_id in counters_db.heroes:
                hero_counters = counters_db.heroes[hero_id]
                legacy_hero["counters"] = [
                    {
                        "hero_id": c.hero_id,
                        "hero_name": c.hero_name,
                        "localized_name": c.localized_name,
                        "reason": c.reason
                    }
                    for c in hero_counters.counters
                ]
                legacy_hero["good_against"] = [
                    {
                        "hero_id": g.hero_id,
                        "hero_name": g.hero_name,
                        "localized_name": g.localized_name,
                        "reason": g.reason
                    }
                    for g in hero_counters.good_against
                ]
                legacy_hero["when_to_pick"] = hero_counters.when_to_pick

            legacy_heroes[hero_key] = legacy_hero

        return legacy_heroes

    def _map_attribute(self, primary_attr: str) -> str:
        """Map dotaconstants attribute format to legacy format."""
        attr_map = {
            "str": "strength",
            "agi": "agility",
            "int": "intelligence",
            "all": "universal"
        }
        return attr_map.get(primary_attr, "strength")

    def _generate_aliases(self, hero_data: Dict[str, Any]) -> list[str]:
        """Generate aliases from hero data."""
        aliases = []

        localized_name = hero_data.get("localized_name", "").lower()
        if localized_name:
            aliases.append(localized_name)

            # Add common abbreviations and alternative names
            words = localized_name.split()
            if len(words) > 1:
                # Add abbreviation (first letters)
                abbrev = ''.join(word[0] for word in words if word)
                if len(abbrev) > 1:
                    aliases.append(abbrev)

            # Add without special characters
            clean_name = localized_name.replace("-", "").replace("'", "").replace(" ", "")
            if clean_name != localized_name:
                aliases.append(clean_name)

        return aliases

    async def get_all_heroes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all heroes data in legacy format.

        Returns:
            Dictionary with hero internal names as keys and hero data as values
        """
        heroes_constants = self.constants.get_heroes_constants()

        if not heroes_constants:
            logger.warning("Heroes constants not available, attempting to fetch...")
            try:
                await self.constants.fetch_constants_file("heroes.json")
                heroes_constants = self.constants.get_heroes_constants()
            except Exception as e:
                logger.error(f"Failed to fetch heroes constants: {e}")
                return {}

        if heroes_constants:
            return self._convert_constants_to_legacy_format(heroes_constants)

        return {}

    def get_heroes_constants_raw(self) -> Dict[str, Dict[str, Any]]:
        """
        Get raw heroes constants data (full dotaconstants format).

        Returns:
            Raw heroes data from dotaconstants with all fields
        """
        heroes_constants = self.constants.get_heroes_constants()
        return heroes_constants or {}

    async def get_heroes_in_match(self, match_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get full hero constants data for heroes playing in a given match.

        Args:
            match_id: The Dota 2 match ID

        Returns:
            Dictionary with hero internal names as keys and full constants data as values,
            filtered to only include the 10 heroes that played in the specified match
        """
        replay_path = await self.replay_downloader.download_replay(match_id)

        if not replay_path:
            logger.error(f"Could not download replay for match {match_id}")
            return {}

        try:
            from python_manta import Parser

            parser = Parser(str(replay_path))
            result = parser.parse(game_info=True)

            if not result.success:
                logger.error(f"Failed to parse game info for match {match_id}: {result.error}")
                return {}

            if not result.game_info:
                logger.error(f"No game info in parse result for match {match_id}")
                return {}

            picked_heroes = [Hero(pick.hero_id) for pick in result.game_info.picks_bans
                            if pick.is_pick and pick.hero_id > 0]
            picked_hero_ids = [hero.value for hero in picked_heroes]

            heroes_list = self.constants.enrich_hero_picks(picked_hero_ids)

            heroes = {}
            for hero_data in heroes_list:
                hero_key = hero_data.get("name", f"npc_dota_hero_{hero_data.get('id', 'unknown')}")
                heroes[hero_key] = hero_data

            return heroes

        except ImportError:
            logger.error("Draft parser not available. Please ensure python_manta is installed.")
            return {}
        except Exception as e:
            logger.error(f"Error parsing match {match_id}: {e}")
            return {}

    async def get_match_heroes(self, match_id: int) -> List[Dict[str, Any]]:
        """
        Get hero and player data for a match.

        Args:
            match_id: The Dota 2 match ID

        Returns:
            List of player data with hero info, lane, and role
        """
        fetcher = MatchFetcher()
        players = await fetcher.get_players(match_id)

        if not players:
            logger.error(f"Could not fetch player data for match {match_id}")
            return []

        heroes_constants = self.get_heroes_constants_raw()
        manual_pro_names = pro_scene_fetcher.get_manual_pro_names()
        counters_db = self._load_hero_counters()

        result = []
        for player in players:
            hero_id = player.get("hero_id")
            if not hero_id:
                continue

            hero_data = heroes_constants.get(str(hero_id), {})

            merged = {
                **player,
                "hero_name": hero_data.get("name", f"npc_dota_hero_{hero_id}"),
                "localized_name": hero_data.get("localized_name", "Unknown"),
                "primary_attr": hero_data.get("primary_attr"),
                "attack_type": hero_data.get("attack_type"),
                "roles": hero_data.get("roles", []),
                "counters": [],
                "good_against": [],
                "when_to_pick": [],
            }

            if counters_db and str(hero_id) in counters_db.heroes:
                hero_counters = counters_db.heroes[str(hero_id)]
                merged["counters"] = [
                    {"hero_id": c.hero_id, "localized_name": c.localized_name, "reason": c.reason}
                    for c in hero_counters.counters
                ]
                merged["good_against"] = [
                    {"hero_id": g.hero_id, "localized_name": g.localized_name, "reason": g.reason}
                    for g in hero_counters.good_against
                ]
                merged["when_to_pick"] = hero_counters.when_to_pick

            # Enrich with manual pro names if OpenDota doesn't have pro_name
            account_id = player.get("account_id")
            if account_id and not merged.get("pro_name"):
                manual_name = manual_pro_names.get(str(account_id))
                if manual_name:
                    merged["pro_name"] = manual_name
                    merged["player_name"] = manual_name

            result.append(merged)

        result.sort(key=lambda x: (x.get("team", ""), x.get("lane", 0)))

        return result

    def search_heroes_by_role(self, role: str) -> Dict[str, Dict[str, Any]]:
        """
        Search heroes by their role using constants data.

        Args:
            role: The role to search for (e.g., "Carry", "Support", "Initiator")

        Returns:
            Dictionary of heroes that have the specified role
        """
        heroes_constants = self.get_heroes_constants_raw()
        matching_heroes = {}

        for hero_id, hero_data in heroes_constants.items():
            roles = hero_data.get("roles", [])
            if role in roles:
                hero_key = hero_data.get("name", f"npc_dota_hero_{hero_id}")
                matching_heroes[hero_key] = hero_data

        return matching_heroes

    def get_heroes_by_attribute(self, attribute: str) -> Dict[str, Dict[str, Any]]:
        """
        Get heroes filtered by primary attribute.

        Args:
            attribute: Primary attribute ("str", "agi", "int", or "all")

        Returns:
            Dictionary of heroes with the specified primary attribute
        """
        heroes_constants = self.get_heroes_constants_raw()
        matching_heroes = {}

        for hero_id, hero_data in heroes_constants.items():
            if hero_data.get("primary_attr") == attribute:
                hero_key = hero_data.get("name", f"npc_dota_hero_{hero_id}")
                matching_heroes[hero_key] = hero_data

        return matching_heroes


# Create a singleton instance
heroes_resource = HeroesResource()
