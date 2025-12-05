"""Pro scene resources for players, teams, and leagues."""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from opendota import OpenDota

from src.models.pro_scene import (
    LeagueInfo,
    LeagueMatchesResponse,
    LeaguesResponse,
    PlayerSearchResponse,
    ProMatchesResponse,
    ProMatchSummary,
    ProPlayerInfo,
    ProPlayerResponse,
    RosterEntry,
    SeriesSummary,
    TeamInfo,
    TeamMatchesResponse,
    TeamResponse,
    TeamSearchResponse,
)
from src.utils.player_fuzzy_search import player_fuzzy_search
from src.utils.pro_scene_fetcher import pro_scene_fetcher
from src.utils.team_fuzzy_search import team_fuzzy_search

logger = logging.getLogger(__name__)


class ProSceneResource:
    """Resource for accessing pro scene data."""

    def __init__(self):
        self._initialized = False

    async def initialize(self, force: bool = False) -> None:
        """Initialize the resource by fetching data from OpenDota."""
        if self._initialized and not force:
            return

        players = await pro_scene_fetcher.fetch_pro_players(force=force)
        teams = await pro_scene_fetcher.fetch_teams(force=force)

        player_aliases = pro_scene_fetcher.get_player_aliases()
        team_aliases = pro_scene_fetcher.get_team_aliases()

        player_fuzzy_search.initialize(players, player_aliases)
        team_fuzzy_search.initialize(teams, team_aliases)

        self._initialized = True
        logger.info("Pro scene resource initialized")

    async def _ensure_initialized(self) -> None:
        """Ensure resource is initialized before use."""
        if not self._initialized:
            await self.initialize()

    async def search_player(
        self, query: str, threshold: float = 0.6, max_results: int = 10
    ) -> PlayerSearchResponse:
        """Search for players by name or alias."""
        await self._ensure_initialized()

        try:
            results = player_fuzzy_search.search(query, threshold, max_results)
            return PlayerSearchResponse(
                success=True,
                query=query,
                total_results=len(results),
                results=results,
            )
        except Exception as e:
            logger.error(f"Error searching players: {e}")
            return PlayerSearchResponse(
                success=False,
                query=query,
                error=str(e),
            )

    async def search_team(
        self, query: str, threshold: float = 0.6, max_results: int = 10
    ) -> TeamSearchResponse:
        """Search for teams by name, tag, or alias."""
        await self._ensure_initialized()

        try:
            results = team_fuzzy_search.search(query, threshold, max_results)
            return TeamSearchResponse(
                success=True,
                query=query,
                total_results=len(results),
                results=results,
            )
        except Exception as e:
            logger.error(f"Error searching teams: {e}")
            return TeamSearchResponse(
                success=False,
                query=query,
                error=str(e),
            )

    async def get_player(self, account_id: int) -> ProPlayerResponse:
        """Get player details by account ID."""
        await self._ensure_initialized()

        try:
            players = await pro_scene_fetcher.fetch_pro_players()

            for p in players:
                if p.get("account_id") == account_id:
                    aliases = pro_scene_fetcher.get_player_aliases()
                    player_aliases = aliases.get(str(account_id), [])

                    player_info = ProPlayerInfo(
                        account_id=p["account_id"],
                        name=p.get("name") or p.get("personaname") or "Unknown",
                        personaname=p.get("personaname"),
                        team_id=p.get("team_id"),
                        team_name=p.get("team_name"),
                        team_tag=p.get("team_tag"),
                        country_code=p.get("country_code"),
                        fantasy_role=p.get("fantasy_role"),
                        is_active=not p.get("is_locked", False),
                        aliases=player_aliases,
                    )

                    return ProPlayerResponse(success=True, player=player_info)

            return ProPlayerResponse(
                success=False,
                error=f"Player with account_id {account_id} not found",
            )

        except Exception as e:
            logger.error(f"Error getting player {account_id}: {e}")
            return ProPlayerResponse(success=False, error=str(e))

    async def get_player_by_name(self, name: str) -> ProPlayerResponse:
        """Get player by fuzzy name search."""
        await self._ensure_initialized()

        match = player_fuzzy_search.find_best_match(name)
        if not match:
            return ProPlayerResponse(
                success=False,
                error=f"No player found matching '{name}'",
            )

        return await self.get_player(match.id)

    async def get_team(self, team_id: int) -> TeamResponse:
        """Get team details including roster."""
        await self._ensure_initialized()

        try:
            team_details = await pro_scene_fetcher.fetch_team_details(team_id)

            team_data = team_details.get("team", {})
            players_data = team_details.get("players", [])

            aliases = pro_scene_fetcher.get_team_aliases()
            team_aliases = aliases.get(str(team_id), [])

            team_info = TeamInfo(
                team_id=team_id,
                name=team_data.get("name") or "Unknown",
                tag=team_data.get("tag") or "",
                logo_url=team_data.get("logo_url"),
                rating=team_data.get("rating") or 0.0,
                wins=team_data.get("wins") or 0,
                losses=team_data.get("losses") or 0,
                aliases=team_aliases,
            )

            roster = []
            for p in players_data:
                roster.append(
                    RosterEntry(
                        account_id=p["account_id"],
                        player_name=p.get("name") or "Unknown",
                        team_id=team_id,
                        games_played=p.get("games_played") or 0,
                        wins=p.get("wins") or 0,
                        is_current=p.get("is_current_team_member") or False,
                    )
                )

            return TeamResponse(success=True, team=team_info, roster=roster)

        except Exception as e:
            logger.error(f"Error getting team {team_id}: {e}")
            return TeamResponse(success=False, error=str(e))

    async def get_team_by_name(self, name: str) -> TeamResponse:
        """Get team by fuzzy name search."""
        await self._ensure_initialized()

        match = team_fuzzy_search.find_best_match(name)
        if not match:
            return TeamResponse(
                success=False,
                error=f"No team found matching '{name}'",
            )

        return await self.get_team(match.id)

    async def get_team_matches(
        self, team_id: int, limit: int = 50
    ) -> TeamMatchesResponse:
        """Get recent matches for a team."""
        await self._ensure_initialized()

        try:
            team_details = await pro_scene_fetcher.fetch_team_details(team_id)

            team_data = team_details.get("team", {})
            matches_data = team_details.get("recent_matches", [])

            matches = []
            for m in matches_data[:limit]:
                is_radiant = m.get("radiant", False)

                radiant_team_id = team_id if is_radiant else m.get("opposing_team_id")
                dire_team_id = m.get("opposing_team_id") if is_radiant else team_id
                radiant_team_name = (
                    team_data.get("name")
                    if is_radiant
                    else m.get("opposing_team_name")
                )
                dire_team_name = (
                    m.get("opposing_team_name")
                    if is_radiant
                    else team_data.get("name")
                )

                matches.append(
                    ProMatchSummary(
                        match_id=m["match_id"],
                        radiant_team_id=radiant_team_id,
                        radiant_team_name=radiant_team_name,
                        dire_team_id=dire_team_id,
                        dire_team_name=dire_team_name,
                        radiant_win=m.get("radiant_win") or False,
                        duration=m.get("duration") or 0,
                        start_time=m.get("start_time") or 0,
                        league_id=m.get("leagueid"),
                        league_name=m.get("league_name"),
                    )
                )

            return TeamMatchesResponse(
                success=True,
                team_id=team_id,
                team_name=team_data.get("name"),
                total_matches=len(matches),
                matches=matches,
            )

        except Exception as e:
            logger.error(f"Error getting matches for team {team_id}: {e}")
            return TeamMatchesResponse(
                success=False,
                team_id=team_id,
                error=str(e),
            )

    async def get_leagues(self, tier: Optional[str] = None) -> LeaguesResponse:
        """Get all leagues, optionally filtered by tier."""
        await self._ensure_initialized()

        try:
            leagues_data = await pro_scene_fetcher.fetch_leagues()

            leagues = []
            for lg in leagues_data:
                league_tier = lg.get("tier")

                if tier and league_tier != tier:
                    continue

                leagues.append(
                    LeagueInfo(
                        league_id=lg["leagueid"],
                        name=lg.get("name") or "Unknown",
                        tier=league_tier,
                    )
                )

            return LeaguesResponse(
                success=True,
                total_leagues=len(leagues),
                leagues=leagues,
            )

        except Exception as e:
            logger.error(f"Error getting leagues: {e}")
            return LeaguesResponse(success=False, error=str(e))

    async def add_player_alias(self, account_id: int, alias: str) -> bool:
        """Add a manual alias for a player."""
        try:
            pro_scene_fetcher.add_player_alias(account_id, alias)
            await self.initialize(force=True)
            return True
        except Exception as e:
            logger.error(f"Error adding player alias: {e}")
            return False

    async def add_team_alias(self, team_id: int, alias: str) -> bool:
        """Add a manual alias for a team."""
        try:
            pro_scene_fetcher.add_team_alias(team_id, alias)
            await self.initialize(force=True)
            return True
        except Exception as e:
            logger.error(f"Error adding team alias: {e}")
            return False

    async def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all pro players (raw data)."""
        await self._ensure_initialized()
        return await pro_scene_fetcher.fetch_pro_players()

    async def get_all_teams(self) -> List[Dict[str, Any]]:
        """Get all teams (raw data)."""
        await self._ensure_initialized()
        return await pro_scene_fetcher.fetch_teams()

    def _series_type_to_name(self, series_type: int) -> str:
        """Convert series_type to human-readable name."""
        return {0: "Bo1", 1: "Bo3", 2: "Bo5"}.get(series_type, f"Bo{series_type}")

    def _wins_needed(self, series_type: int) -> int:
        """Calculate wins needed to win the series."""
        return {0: 1, 1: 2, 2: 3}.get(series_type, 1)

    def _group_matches_into_series(
        self, matches: List[ProMatchSummary]
    ) -> Tuple[List[ProMatchSummary], List[SeriesSummary]]:
        """Group matches by series_id and compute series results."""
        series_matches: Dict[int, List[ProMatchSummary]] = defaultdict(list)
        standalone_matches: List[ProMatchSummary] = []

        for match in matches:
            if match.series_id:
                series_matches[match.series_id].append(match)
            else:
                standalone_matches.append(match)

        series_list: List[SeriesSummary] = []

        for series_id, games in series_matches.items():
            games_sorted = sorted(games, key=lambda g: g.start_time)

            for i, game in enumerate(games_sorted):
                game.game_number = i + 1

            first_game = games_sorted[0]
            series_type = first_game.series_type or 0

            team1_id = first_game.radiant_team_id
            team1_name = first_game.radiant_team_name
            team2_id = first_game.dire_team_id
            team2_name = first_game.dire_team_name

            team1_wins = 0
            team2_wins = 0

            for game in games_sorted:
                if game.radiant_win:
                    if game.radiant_team_id == team1_id:
                        team1_wins += 1
                    else:
                        team2_wins += 1
                else:
                    if game.dire_team_id == team1_id:
                        team1_wins += 1
                    else:
                        team2_wins += 1

            wins_needed = self._wins_needed(series_type)
            is_complete = team1_wins >= wins_needed or team2_wins >= wins_needed

            winner_id = None
            winner_name = None
            if team1_wins >= wins_needed:
                winner_id = team1_id
                winner_name = team1_name
            elif team2_wins >= wins_needed:
                winner_id = team2_id
                winner_name = team2_name

            series_list.append(
                SeriesSummary(
                    series_id=series_id,
                    series_type=series_type,
                    series_type_name=self._series_type_to_name(series_type),
                    team1_id=team1_id,
                    team1_name=team1_name,
                    team1_wins=team1_wins,
                    team2_id=team2_id,
                    team2_name=team2_name,
                    team2_wins=team2_wins,
                    winner_id=winner_id,
                    winner_name=winner_name,
                    is_complete=is_complete,
                    league_id=first_game.league_id,
                    league_name=first_game.league_name,
                    start_time=first_game.start_time,
                    games=games_sorted,
                )
            )

        series_list.sort(key=lambda s: s.start_time, reverse=True)

        all_matches = standalone_matches + [
            game for series in series_list for game in series.games
        ]
        all_matches.sort(key=lambda m: m.start_time, reverse=True)

        return all_matches, series_list

    async def get_pro_matches(self, limit: int = 100) -> ProMatchesResponse:
        """Get recent pro matches with series grouping."""
        try:
            async with OpenDota(format="json") as client:
                raw_matches = await client.get_pro_matches()

            matches = []
            for m in raw_matches[:limit]:
                matches.append(
                    ProMatchSummary(
                        match_id=m.get("match_id"),
                        radiant_team_id=m.get("radiant_team_id"),
                        radiant_team_name=m.get("radiant_name"),
                        dire_team_id=m.get("dire_team_id"),
                        dire_team_name=m.get("dire_name"),
                        radiant_win=m.get("radiant_win", False),
                        radiant_score=m.get("radiant_score", 0),
                        dire_score=m.get("dire_score", 0),
                        duration=m.get("duration", 0),
                        start_time=m.get("start_time", 0),
                        league_id=m.get("leagueid"),
                        league_name=m.get("league_name"),
                        series_id=m.get("series_id"),
                        series_type=m.get("series_type"),
                    )
                )

            all_matches, series_list = self._group_matches_into_series(matches)

            return ProMatchesResponse(
                success=True,
                total_matches=len(all_matches),
                total_series=len(series_list),
                matches=all_matches,
                series=series_list,
            )

        except Exception as e:
            logger.error(f"Error getting pro matches: {e}")
            return ProMatchesResponse(success=False, error=str(e))

    async def get_league_matches(
        self, league_id: int, limit: int = 100
    ) -> LeagueMatchesResponse:
        """Get matches from a specific league/tournament with series grouping."""
        try:
            async with OpenDota(format="json") as client:
                raw_matches = await client.get_league_matches(league_id, limit=limit)
                league_data = await client.get_league(league_id)

            league_name = None
            if league_data:
                league_name = league_data.get("name")

            matches = []
            for m in raw_matches:
                matches.append(
                    ProMatchSummary(
                        match_id=m.get("match_id"),
                        radiant_team_id=m.get("radiant_team_id"),
                        radiant_team_name=m.get("radiant_name"),
                        dire_team_id=m.get("dire_team_id"),
                        dire_team_name=m.get("dire_name"),
                        radiant_win=m.get("radiant_win", False),
                        radiant_score=m.get("radiant_score", 0),
                        dire_score=m.get("dire_score", 0),
                        duration=m.get("duration", 0),
                        start_time=m.get("start_time", 0),
                        league_id=league_id,
                        league_name=league_name,
                        series_id=m.get("series_id"),
                        series_type=m.get("series_type"),
                    )
                )

            all_matches, series_list = self._group_matches_into_series(matches)

            return LeagueMatchesResponse(
                success=True,
                league_id=league_id,
                league_name=league_name,
                total_matches=len(all_matches),
                total_series=len(series_list),
                matches=all_matches,
                series=series_list,
            )

        except Exception as e:
            logger.error(f"Error getting league matches for {league_id}: {e}")
            return LeagueMatchesResponse(
                success=False,
                league_id=league_id,
                error=str(e),
            )


pro_scene_resource = ProSceneResource()
