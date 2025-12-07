"""
Timeline parser for extracting time-series data from Dota 2 replays.

Uses v2 ParsedReplayData from ReplayService.
"""

import logging
from typing import Any, Dict, List, Optional

from src.services.models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)


class TimelineParser:
    """Parses replay files to extract timeline data using v2 ParsedReplayData."""

    def parse_timeline(self, data: ParsedReplayData) -> Optional[Dict[str, Any]]:
        """
        Parse timeline data from parsed replay data.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            Dictionary with timeline data for all players, or None on error
        """
        if data.metadata is None:
            logger.error("No metadata found in replay")
            return None

        metadata = data.metadata.get('metadata', {})
        teams = metadata.get('teams', [])

        if len(teams) < 2:
            logger.error("Not enough team data in replay")
            return None

        players = []
        for team_idx, team in enumerate(teams[:2]):
            team_name = "radiant" if team_idx == 0 else "dire"

            for player in team.get('players', []):
                player_data = self._extract_player_timeline(player, team_name)
                if player_data:
                    players.append(player_data)

        team_graphs = self._extract_team_graphs(teams[:2])

        # Merge entity data from cache
        self._merge_entity_data(players, data.entity_snapshots)

        return {
            "match_id": data.metadata.get('match_id') if data.metadata else data.match_id,
            "players": players,
            "radiant": team_graphs.get("radiant", {}),
            "dire": team_graphs.get("dire", {}),
        }

    def _extract_player_timeline(self, player: Dict[str, Any], team: str) -> Optional[Dict[str, Any]]:
        """Extract timeline data for a single player."""
        player_slot = player.get('player_slot')
        if player_slot is None:
            return None

        graph_nw = player.get('graph_net_worth', [])
        graph_dmg = player.get('graph_hero_damage', [])
        snapshots = player.get('inventory_snapshot', [])

        kda_timeline = []
        for snap in snapshots:
            gt = snap.get('game_time', 0)
            if gt >= 0:
                kda_timeline.append({
                    "game_time": gt,
                    "kills": snap.get('kills', 0),
                    "deaths": snap.get('deaths', 0),
                    "assists": snap.get('assists', 0),
                    "level": snap.get('level', 1),
                })

        return {
            "player_slot": player_slot,
            "team": team,
            "game_player_id": player.get('game_player_id'),
            "net_worth": graph_nw,
            "hero_damage": graph_dmg,
            "kda_timeline": kda_timeline,
        }

    def _extract_team_graphs(self, teams: List[Dict[str, Any]]) -> Dict[str, Dict[str, List]]:
        """Extract team-level graph data."""
        result = {}
        for idx, team in enumerate(teams):
            team_name = "radiant" if idx == 0 else "dire"
            result[team_name] = {
                "graph_experience": team.get('graph_experience', []),
                "graph_gold_earned": team.get('graph_gold_earned', []),
                "graph_net_worth": team.get('graph_net_worth', []),
            }
        return result

    def _merge_entity_data(self, players: List[Dict[str, Any]], entity_snapshots: list) -> None:
        """
        Merge entity data (last_hits, denies) into player timeline data.

        Args:
            players: List of player timeline dicts to update in place
            entity_snapshots: Entity snapshots from v2 (python-manta EntitySnapshot)
        """
        # Build player_id to timeline data mapping
        player_timeline: Dict[int, List[Dict[str, Any]]] = {}

        for snap in entity_snapshots:
            # Skip draft phase snapshots (game_time is 0.0 during draft)
            if snap.game_time <= 0:
                continue

            game_min = int(snap.game_time / 60)

            # v2 uses snap.heroes instead of snap.players
            for hero in snap.heroes:
                player_id = hero.player_id
                if player_id is None:
                    continue

                if player_id not in player_timeline:
                    player_timeline[player_id] = []

                player_timeline[player_id].append({
                    "game_time": snap.game_time,
                    "minute": game_min,
                    "last_hits": hero.last_hits,
                    "denies": hero.denies,
                    "gold": hero.gold,
                    "level": hero.level,
                    "hero_id": getattr(hero, 'hero_id', 0),
                })

        # Merge into players
        for player in players:
            player_id = player.get('game_player_id')
            if player_id is not None and player_id in player_timeline:
                snapshots = player_timeline[player_id]
                player['last_hits'] = [s['last_hits'] for s in snapshots]
                player['denies'] = [s['denies'] for s in snapshots]
                player['entity_timeline'] = snapshots

    def get_stats_at_minute(self, timeline: Dict[str, Any], minute: int) -> Dict[str, Any]:
        """
        Get player stats at a specific minute.

        Args:
            timeline: Timeline data from parse_timeline
            minute: Game minute to get stats for

        Returns:
            Dictionary with per-player stats at that minute
        """
        graph_index = minute * 2

        player_stats = []
        for player in timeline.get('players', []):
            nw_list = player.get('net_worth', [])
            dmg_list = player.get('hero_damage', [])
            kda = player.get('kda_timeline', [])
            entity_timeline = player.get('entity_timeline', [])

            nw = nw_list[graph_index] if graph_index < len(nw_list) else nw_list[-1] if nw_list else 0
            dmg = dmg_list[graph_index] if graph_index < len(dmg_list) else dmg_list[-1] if dmg_list else 0

            kda_at_min = None
            for entry in kda:
                if entry.get('game_time', 0) <= minute * 60:
                    kda_at_min = entry
                else:
                    break

            entity_at_min = None
            for entry in entity_timeline:
                if entry.get('minute', 0) <= minute:
                    entity_at_min = entry
                else:
                    break

            stat = {
                "player_slot": player.get('player_slot'),
                "team": player.get('team'),
                "net_worth": round(nw, 2) if nw else 0,
                "hero_damage": round(dmg, 2) if dmg else 0,
            }
            if kda_at_min:
                stat.update({
                    "kills": kda_at_min.get('kills', 0),
                    "deaths": kda_at_min.get('deaths', 0),
                    "assists": kda_at_min.get('assists', 0),
                    "level": kda_at_min.get('level', 1),
                })
            if entity_at_min:
                stat.update({
                    "last_hits": entity_at_min.get('last_hits', 0),
                    "denies": entity_at_min.get('denies', 0),
                })
            player_stats.append(stat)

        return {
            "minute": minute,
            "players": player_stats,
        }


timeline_parser = TimelineParser()
