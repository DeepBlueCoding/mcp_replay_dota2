"""
Match info parser for extracting match metadata and draft from Dota 2 replays.

Uses Parser.parse(game_info=True) to extract pro match data including
teams, players, draft order, and match outcome.
"""

import logging
from pathlib import Path
from typing import Optional

from python_manta import Parser, Team

from src.models.match_info import (
    DraftAction,
    DraftResult,
    MatchInfoResult,
    PlayerInfo,
    TeamInfo,
)
from src.utils.constants_fetcher import constants_fetcher

logger = logging.getLogger(__name__)

GAME_MODES = {
    0: "Unknown",
    1: "All Pick",
    2: "Captains Mode",
    3: "Random Draft",
    4: "Single Draft",
    5: "All Random",
    6: "Intro",
    7: "Diretide",
    8: "Reverse Captains Mode",
    9: "The Greeviling",
    10: "Tutorial",
    11: "Mid Only",
    12: "Least Played",
    13: "Limited Heroes",
    14: "Compendium Matchmaking",
    15: "Custom",
    16: "Captains Draft",
    17: "Balanced Draft",
    18: "Ability Draft",
    19: "Event",
    20: "All Random Death Match",
    21: "1v1 Mid",
    22: "All Draft",
    23: "Turbo",
    24: "Mutation",
}


class MatchInfoParser:
    """Parses match info and draft data from Dota 2 replays."""

    def __init__(self):
        pass

    def _get_hero_info(self, hero_id: int) -> tuple[str, str]:
        """Get hero internal name and localized name from hero_id."""
        heroes = constants_fetcher.get_heroes_constants()
        hero_data = heroes.get(str(hero_id), {})

        name = hero_data.get("name", f"npc_dota_hero_{hero_id}")
        if name.startswith("npc_dota_hero_"):
            internal_name = name[14:]
        else:
            internal_name = name

        localized = hero_data.get("localized_name", internal_name.replace("_", " ").title())
        return internal_name, localized

    def _format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def get_draft(self, replay_path: Path) -> Optional[DraftResult]:
        """
        Get draft information from a replay using v2 API.

        Args:
            replay_path: Path to the .dem replay file

        Returns:
            DraftResult with all picks and bans in order, or None on error
        """
        try:
            parser = Parser(str(replay_path))
            result = parser.parse(game_info=True)

            if not result.success:
                logger.error(f"Failed to parse game info: {result.error}")
                return None

            game_info = result.game_info
            if not game_info:
                logger.error("No game info in parse result")
                return None

            actions = []
            radiant_picks = []
            radiant_bans = []
            dire_picks = []
            dire_bans = []

            for i, pb in enumerate(game_info.picks_bans):
                team = "radiant" if pb.team == Team.RADIANT.value else "dire"
                hero_name, hero_localized = self._get_hero_info(pb.hero_id)

                action = DraftAction(
                    order=i + 1,
                    is_pick=pb.is_pick,
                    team=team,
                    hero_id=pb.hero_id,
                    hero_name=hero_name,
                    localized_name=hero_localized,
                )
                actions.append(action)

                if pb.is_pick:
                    if team == "radiant":
                        radiant_picks.append(action)
                    else:
                        dire_picks.append(action)
                else:
                    if team == "radiant":
                        radiant_bans.append(action)
                    else:
                        dire_bans.append(action)

            return DraftResult(
                match_id=game_info.match_id,
                game_mode=game_info.game_mode,
                game_mode_name=GAME_MODES.get(game_info.game_mode, f"Unknown ({game_info.game_mode})"),
                actions=actions,
                radiant_picks=radiant_picks,
                radiant_bans=radiant_bans,
                dire_picks=dire_picks,
                dire_bans=dire_bans,
            )

        except Exception as e:
            logger.error(f"Error parsing draft: {e}")
            return None

    def get_match_info(self, replay_path: Path) -> Optional[MatchInfoResult]:
        """
        Get match information from a replay using v2 API.

        Args:
            replay_path: Path to the .dem replay file

        Returns:
            MatchInfoResult with teams, players, winner, duration, etc.
        """
        try:
            parser = Parser(str(replay_path))
            result = parser.parse(game_info=True)

            if not result.success:
                logger.error(f"Failed to parse game info: {result.error}")
                return None

            game_info = result.game_info
            if not game_info:
                logger.error("No game info in parse result")
                return None

            winner = "radiant" if game_info.game_winner == Team.RADIANT.value else "dire"

            radiant_team = TeamInfo(
                team_id=game_info.radiant_team_id,
                team_tag=game_info.radiant_team_tag,
                team_name=game_info.radiant_team_tag if game_info.radiant_team_tag else "Radiant",
            )

            dire_team = TeamInfo(
                team_id=game_info.dire_team_id,
                team_tag=game_info.dire_team_tag,
                team_name=game_info.dire_team_tag if game_info.dire_team_tag else "Dire",
            )

            players = []
            radiant_players = []
            dire_players = []

            for p in game_info.players:
                hero_name = p.hero_name
                if hero_name.startswith("npc_dota_hero_"):
                    hero_internal = hero_name[14:]
                else:
                    hero_internal = hero_name

                _, hero_localized = self._get_hero_info(0)
                heroes = constants_fetcher.get_heroes_constants()
                for hid, hdata in heroes.items():
                    if hdata.get("name") == p.hero_name:
                        hero_localized = hdata.get("localized_name", hero_internal.replace("_", " ").title())
                        hero_id = int(hid)
                        break
                else:
                    hero_id = 0
                    hero_localized = hero_internal.replace("_", " ").title()

                team = "radiant" if p.team == Team.RADIANT.value else "dire"

                player_info = PlayerInfo(
                    player_name=p.player_name,
                    hero_name=hero_internal,
                    hero_localized=hero_localized,
                    hero_id=hero_id,
                    team=team,
                    steam_id=p.steam_id,
                )
                players.append(player_info)

                if team == "radiant":
                    radiant_players.append(player_info)
                else:
                    dire_players.append(player_info)

            is_pro = game_info.radiant_team_id > 0 or game_info.dire_team_id > 0 or game_info.league_id > 0

            return MatchInfoResult(
                match_id=game_info.match_id,
                is_pro_match=is_pro,
                league_id=game_info.league_id,
                game_mode=game_info.game_mode,
                game_mode_name=GAME_MODES.get(game_info.game_mode, f"Unknown ({game_info.game_mode})"),
                winner=winner,
                duration_seconds=game_info.playback_time,
                duration_str=self._format_duration(game_info.playback_time),
                radiant_team=radiant_team,
                dire_team=dire_team,
                players=players,
                radiant_players=radiant_players,
                dire_players=dire_players,
            )

        except Exception as e:
            logger.error(f"Error parsing match info: {e}")
            return None


match_info_parser = MatchInfoParser()
