"""
Match data fetcher using OpenDota API.
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

OPENDOTA_API_URL = "https://api.opendota.com/api"

LANE_NAMES = {
    1: "safe_lane",
    2: "mid_lane",
    3: "off_lane",
    4: "jungle",
}


def assign_roles(players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Assign core/support role based on lane and net worth.

    Within each lane, higher net worth = core, lower = support.
    """
    radiant = [p for p in players if p.get("player_slot", 0) < 128]
    dire = [p for p in players if p.get("player_slot", 0) >= 128]

    def process_team(team_players: List[Dict[str, Any]]) -> None:
        lanes = {}
        for player in team_players:
            lane = player.get("lane")
            if lane not in lanes:
                lanes[lane] = []
            lanes[lane].append(player)

        for lane, lane_players in lanes.items():
            if len(lane_players) == 1:
                lane_players[0]["role"] = "core"
            else:
                sorted_by_nw = sorted(
                    lane_players,
                    key=lambda p: p.get("net_worth", 0),
                    reverse=True
                )
                sorted_by_nw[0]["role"] = "core"
                for p in sorted_by_nw[1:]:
                    p["role"] = "support"

    process_team(radiant)
    process_team(dire)

    return players


class MatchFetcher:
    """Fetches match data from OpenDota API."""

    async def get_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch match data from OpenDota API."""
        url = f"{OPENDOTA_API_URL}/matches/{match_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to fetch match {match_id}: HTTP {response.status}")
                return None

    async def get_players(self, match_id: int) -> List[Dict[str, Any]]:
        """Get player data for a match with lane and role info."""
        match = await self.get_match(match_id)
        if not match:
            return []

        players = match.get("players", [])
        players = assign_roles(players)

        result = []
        for player in players:
            result.append(self._build_player(player))

        return result

    async def get_timeline(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get time-series data (gold, xp, lh, dn per minute) for all players."""
        match = await self.get_match(match_id)
        if not match:
            return None

        duration_minutes = match.get("duration", 0) // 60

        players = []
        for player in match.get("players", []):
            player_slot = player.get("player_slot", 0)
            is_radiant = player_slot < 128

            players.append({
                "hero_id": player.get("hero_id"),
                "player_slot": player_slot,
                "team": "radiant" if is_radiant else "dire",
                "gold_t": player.get("gold_t", []),
                "xp_t": player.get("xp_t", []),
                "lh_t": player.get("lh_t", []),
                "dn_t": player.get("dn_t", []),
            })

        return {
            "match_id": match_id,
            "duration_minutes": duration_minutes,
            "players": players,
        }

    def _build_player(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """Build player dict with relevant fields."""
        player_slot = player.get("player_slot", 0)
        is_radiant = player_slot < 128
        lane = player.get("lane")

        return {
            "hero_id": player.get("hero_id"),
            "account_id": player.get("account_id"),
            "player_name": player.get("personaname"),
            "pro_name": player.get("name"),
            "player_slot": player_slot,
            "team": "radiant" if is_radiant else "dire",

            "lane": lane,
            "lane_name": LANE_NAMES.get(lane),
            "is_roaming": player.get("is_roaming"),
            "role": player.get("role"),

            "kills": player.get("kills"),
            "deaths": player.get("deaths"),
            "assists": player.get("assists"),

            "last_hits": player.get("last_hits"),
            "denies": player.get("denies"),
            "gold_per_min": player.get("gold_per_min"),
            "xp_per_min": player.get("xp_per_min"),
            "net_worth": player.get("net_worth"),
            "level": player.get("level"),

            "hero_damage": player.get("hero_damage"),
            "tower_damage": player.get("tower_damage"),
            "hero_healing": player.get("hero_healing"),

            "item_0": player.get("item_0"),
            "item_1": player.get("item_1"),
            "item_2": player.get("item_2"),
            "item_3": player.get("item_3"),
            "item_4": player.get("item_4"),
            "item_5": player.get("item_5"),
            "item_neutral": player.get("item_neutral"),
        }


match_fetcher = MatchFetcher()
