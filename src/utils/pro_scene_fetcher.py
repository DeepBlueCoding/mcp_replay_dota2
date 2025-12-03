"""Fetches and caches pro scene data from OpenDota API."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from opendota import OpenDota

logger = logging.getLogger(__name__)


class ProSceneFetcher:
    """Fetches and caches pro scene data from OpenDota API."""

    CACHE_EXPIRY = {
        "pro_players.json": 24 * 3600,
        "teams.json": 24 * 3600,
        "leagues.json": 7 * 24 * 3600,
        "player_aliases.json": float("inf"),
        "team_aliases.json": float("inf"),
    }

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self.data_dir = data_dir
        else:
            project_root = Path(__file__).parent.parent.parent
            self.data_dir = project_root / "data" / "pro_scene"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Any] = {}

    def _is_cache_valid(self, filename: str) -> bool:
        cache_file = self.data_dir / filename
        if not cache_file.exists():
            return False

        max_age = self.CACHE_EXPIRY.get(filename, 24 * 3600)
        if max_age == float("inf"):
            return True

        file_age = time.time() - cache_file.stat().st_mtime
        return file_age < max_age

    def _load_from_cache(self, filename: str) -> Optional[Any]:
        if filename in self._cache:
            return self._cache[filename]

        cache_file = self.data_dir / filename
        if cache_file.exists():
            with open(cache_file, "r") as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        return None

    def _save_to_cache(self, filename: str, data: Any) -> None:
        cache_file = self.data_dir / filename
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        self._cache[filename] = data

    async def fetch_pro_players(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch all pro players from OpenDota API."""
        filename = "pro_players.json"

        if not force and self._is_cache_valid(filename):
            cached = self._load_from_cache(filename)
            if cached:
                logger.info(f"Loaded {len(cached)} pro players from cache")
                return cached

        logger.info("Fetching pro players from OpenDota...")
        async with OpenDota(format="json") as client:
            players = await client.get_pro_players()

        self._save_to_cache(filename, players)
        logger.info(f"Cached {len(players)} pro players")
        return players

    async def fetch_teams(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch all teams from OpenDota API."""
        filename = "teams.json"

        if not force and self._is_cache_valid(filename):
            cached = self._load_from_cache(filename)
            if cached:
                logger.info(f"Loaded {len(cached)} teams from cache")
                return cached

        logger.info("Fetching teams from OpenDota...")
        async with OpenDota(format="json") as client:
            teams = await client.get_teams()

        self._save_to_cache(filename, teams)
        logger.info(f"Cached {len(teams)} teams")
        return teams

    async def fetch_team_details(
        self, team_id: int, force: bool = False
    ) -> Dict[str, Any]:
        """Fetch detailed team data including roster and recent matches."""
        filename = f"team_{team_id}.json"

        if not force:
            cached = self._load_from_cache(filename)
            if cached:
                logger.info(f"Loaded team {team_id} details from cache")
                return cached

        logger.info(f"Fetching team {team_id} details from OpenDota...")
        async with OpenDota(format="json") as client:
            team = await client.get_team(team_id)
            players = await client.get_team_players(team_id)
            matches = await client.get_team_matches(team_id, limit=50)

        data = {
            "team": team,
            "players": players,
            "recent_matches": matches,
            "fetched_at": time.time(),
        }

        self._save_to_cache(filename, data)
        return data

    async def fetch_leagues(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch all leagues from OpenDota API."""
        filename = "leagues.json"

        if not force and self._is_cache_valid(filename):
            cached = self._load_from_cache(filename)
            if cached:
                logger.info(f"Loaded {len(cached)} leagues from cache")
                return cached

        logger.info("Fetching leagues from OpenDota...")
        async with OpenDota(format="json") as client:
            leagues = await client.get_leagues()

        self._save_to_cache(filename, leagues)
        logger.info(f"Cached {len(leagues)} leagues")
        return leagues

    def get_player_aliases(self) -> Dict[str, List[str]]:
        """Get manual player aliases."""
        data = self._load_from_cache("player_aliases.json")
        return data if data else {}

    def get_team_aliases(self) -> Dict[str, List[str]]:
        """Get manual team aliases."""
        data = self._load_from_cache("team_aliases.json")
        return data if data else {}

    def add_player_alias(self, account_id: int, alias: str) -> None:
        """Add a manual alias for a player."""
        aliases = self.get_player_aliases()
        key = str(account_id)
        if key not in aliases:
            aliases[key] = []
        if alias.lower() not in [a.lower() for a in aliases[key]]:
            aliases[key].append(alias)
        self._save_to_cache("player_aliases.json", aliases)
        logger.info(f"Added alias '{alias}' for player {account_id}")

    def add_team_alias(self, team_id: int, alias: str) -> None:
        """Add a manual alias for a team."""
        aliases = self.get_team_aliases()
        key = str(team_id)
        if key not in aliases:
            aliases[key] = []
        if alias.lower() not in [a.lower() for a in aliases[key]]:
            aliases[key].append(alias)
        self._save_to_cache("team_aliases.json", aliases)
        logger.info(f"Added alias '{alias}' for team {team_id}")

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()


pro_scene_fetcher = ProSceneFetcher()
