"""Match-related MCP tools: match info, timeline, stats, draft, players."""

from typing import Dict, Optional

from fastmcp import Context

from ..models.tool_responses import (
    HeroPosition,
    HeroPositionsResponse,
    HeroSnapshot,
    HeroStats,
    KDASnapshot,
    MatchDraftResponse,
    MatchHeroesResponse,
    MatchInfoResponse,
    MatchPlayerInfo,
    MatchPlayersResponse,
    MatchTimelineResponse,
    PlayerStatsAtMinute,
    PlayerTimeline,
    SnapshotAtTimeResponse,
    StatsAtMinuteResponse,
    TeamGraphs,
)


def register_match_tools(mcp, services):
    """Register match-related tools with the MCP server."""
    replay_service = services["replay_service"]
    lane_service = services["lane_service"]
    seek_service = services["seek_service"]
    heroes_resource = services["heroes_resource"]
    constants_fetcher = services["constants_fetcher"]
    match_fetcher = services["match_fetcher"]
    pro_scene_fetcher = services["pro_scene_fetcher"]

    async def _get_pro_names_from_opendota(match_id: int) -> Dict[int, str]:
        pro_names: Dict[int, str] = {}
        manual_names = pro_scene_fetcher.get_manual_pro_names()
        try:
            match_data = await match_fetcher.get_match(match_id)
            if match_data and "players" in match_data:
                for player in match_data["players"]:
                    account_id = player.get("account_id")
                    if not account_id:
                        continue
                    steam_id = account_id + 76561197960265728
                    pro_name = player.get("name")
                    if pro_name:
                        pro_names[steam_id] = pro_name
                    elif str(account_id) in manual_names:
                        pro_names[steam_id] = manual_names[str(account_id)]
        except Exception:
            pass
        return pro_names

    @mcp.tool
    async def get_match_timeline(
        match_id: int, ctx: Optional[Context] = None
    ) -> MatchTimelineResponse:
        """Get time-series data for a Dota 2 match."""
        from ..utils.timeline_parser import timeline_parser

        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
        except ValueError as e:
            return MatchTimelineResponse(success=False, match_id=match_id, error=str(e))

        if data.metadata is None:
            return MatchTimelineResponse(
                success=False, match_id=match_id, error="No metadata in replay."
            )

        timeline = timeline_parser.parse_timeline(data)
        if not timeline:
            return MatchTimelineResponse(
                success=False, match_id=match_id, error="Could not parse timeline."
            )

        players = []
        for p in timeline.get("players", []):
            kda_timeline = [
                KDASnapshot(
                    game_time=k.get("game_time", 0),
                    kills=k.get("kills", 0),
                    deaths=k.get("deaths", 0),
                    assists=k.get("assists", 0),
                    level=k.get("level", 0),
                )
                for k in p.get("kda_timeline", [])
            ]
            players.append(
                PlayerTimeline(
                    hero=p.get("hero", ""),
                    team=p.get("team", "radiant"),
                    net_worth=p.get("net_worth", []),
                    hero_damage=p.get("hero_damage", []),
                    kda_timeline=kda_timeline,
                )
            )

        team_graphs_data = timeline.get("team_graphs")
        team_graphs = None
        if team_graphs_data:
            team_graphs = TeamGraphs(
                radiant_xp=team_graphs_data.get("radiant_xp", []),
                dire_xp=team_graphs_data.get("dire_xp", []),
                radiant_gold=team_graphs_data.get("radiant_gold", []),
                dire_gold=team_graphs_data.get("dire_gold", []),
            )

        return MatchTimelineResponse(
            success=True, match_id=match_id, players=players, team_graphs=team_graphs
        )

    @mcp.tool
    async def get_stats_at_minute(
        match_id: int, minute: int, ctx: Optional[Context] = None
    ) -> StatsAtMinuteResponse:
        """Get player stats at a specific minute in a Dota 2 match."""
        from ..utils.timeline_parser import timeline_parser

        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
        except ValueError as e:
            return StatsAtMinuteResponse(
                success=False, match_id=match_id, minute=minute, error=str(e)
            )

        if data.metadata is None:
            return StatsAtMinuteResponse(
                success=False, match_id=match_id, minute=minute, error="No metadata."
            )

        timeline = timeline_parser.parse_timeline(data)
        if not timeline:
            return StatsAtMinuteResponse(
                success=False, match_id=match_id, minute=minute, error="Could not parse."
            )

        stats = timeline_parser.get_stats_at_minute(timeline, minute)
        players = [
            PlayerStatsAtMinute(
                hero=p.get("hero", ""),
                team=p.get("team", "radiant"),
                net_worth=p.get("net_worth", 0),
                hero_damage=p.get("hero_damage", 0),
                kills=p.get("kills", 0),
                deaths=p.get("deaths", 0),
                assists=p.get("assists", 0),
                level=p.get("level", 0),
            )
            for p in stats.get("players", [])
        ]
        return StatsAtMinuteResponse(
            success=True, match_id=match_id, minute=minute, players=players
        )

    async def _get_hero_positions_from_opendota(match_id: int) -> Dict[int, int]:
        """Fetch hero positions (1-5) from OpenDota API."""
        hero_positions: Dict[int, int] = {}
        try:
            match_data = await match_fetcher.get_match(match_id)
            if match_data and "players" in match_data:
                from ..utils.match_fetcher import assign_positions
                players = match_data["players"]
                assign_positions(players)
                for player in players:
                    hero_id = player.get("hero_id")
                    position = player.get("position")
                    if hero_id and position:
                        hero_positions[hero_id] = position
        except Exception:
            pass
        return hero_positions

    @mcp.tool
    async def get_match_draft(
        match_id: int, ctx: Optional[Context] = None
    ) -> MatchDraftResponse:
        """Get the complete draft (picks and bans) for a Dota 2 match with drafting context."""
        from ..utils.match_info_parser import match_info_parser

        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
        except ValueError as e:
            return MatchDraftResponse(success=False, match_id=match_id, error=str(e))

        hero_positions = await _get_hero_positions_from_opendota(match_id)
        try:
            draft = match_info_parser.get_draft(data, hero_positions=hero_positions)
        except Exception as e:
            return MatchDraftResponse(
                success=False, match_id=match_id, error=f"Exception parsing draft: {e}"
            )
        if not draft:
            return MatchDraftResponse(
                success=False, match_id=match_id, error="get_draft returned None (no game_info?)"
            )

        return MatchDraftResponse(success=True, match_id=match_id, draft=draft)

    @mcp.tool
    async def get_match_info(
        match_id: int, ctx: Optional[Context] = None
    ) -> MatchInfoResponse:
        """Get match metadata and player information for a Dota 2 match."""
        from ..utils.match_info_parser import match_info_parser

        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
        except ValueError as e:
            return MatchInfoResponse(success=False, match_id=match_id, error=str(e))

        try:
            match_info = match_info_parser.get_match_info(data)
        except Exception as e:
            return MatchInfoResponse(
                success=False, match_id=match_id, error=f"Exception parsing match info: {e}"
            )
        if not match_info:
            return MatchInfoResponse(
                success=False, match_id=match_id, error="get_match_info returned None (no game_info?)"
            )

        pro_names = await _get_pro_names_from_opendota(match_id)
        if pro_names:
            for player in match_info.players:
                if player.steam_id and player.steam_id in pro_names:
                    player.player_name = pro_names[player.steam_id]
            for player in match_info.radiant_players:
                if player.steam_id and player.steam_id in pro_names:
                    player.player_name = pro_names[player.steam_id]
            for player in match_info.dire_players:
                if player.steam_id and player.steam_id in pro_names:
                    player.player_name = pro_names[player.steam_id]

        return MatchInfoResponse(success=True, match_id=match_id, info=match_info)

    @mcp.tool
    async def get_match_heroes(match_id: int) -> MatchHeroesResponse:
        """Get the 10 heroes in a Dota 2 match with detailed stats."""
        heroes = await heroes_resource.get_match_heroes(match_id)
        if heroes:
            radiant_heroes = [
                HeroStats(
                    hero_id=h.get("hero_id", 0),
                    hero_name=h.get("hero_name", ""),
                    localized_name=h.get("localized_name", ""),
                    team="radiant",
                    player_name=h.get("player_name"),
                    pro_name=h.get("pro_name"),
                    position=h.get("position"),
                    kills=h.get("kills", 0),
                    deaths=h.get("deaths", 0),
                    assists=h.get("assists", 0),
                    last_hits=h.get("last_hits", 0),
                    denies=h.get("denies", 0),
                    gpm=h.get("gold_per_min", 0),
                    xpm=h.get("xp_per_min", 0),
                    net_worth=h.get("net_worth", 0),
                    hero_damage=h.get("hero_damage", 0),
                    tower_damage=h.get("tower_damage", 0),
                    hero_healing=h.get("hero_healing", 0),
                    lane=h.get("lane_name"),
                    role=h.get("role"),
                    items=constants_fetcher.convert_item_ids_to_names(
                        [h.get(f"item_{i}") for i in range(6)]
                    ),
                    item_neutral=constants_fetcher.get_item_name(h.get("item_neutral")),
                )
                for h in heroes
                if h.get("team") == "radiant"
            ]
            dire_heroes = [
                HeroStats(
                    hero_id=h.get("hero_id", 0),
                    hero_name=h.get("hero_name", ""),
                    localized_name=h.get("localized_name", ""),
                    team="dire",
                    player_name=h.get("player_name"),
                    pro_name=h.get("pro_name"),
                    position=h.get("position"),
                    kills=h.get("kills", 0),
                    deaths=h.get("deaths", 0),
                    assists=h.get("assists", 0),
                    last_hits=h.get("last_hits", 0),
                    denies=h.get("denies", 0),
                    gpm=h.get("gold_per_min", 0),
                    xpm=h.get("xp_per_min", 0),
                    net_worth=h.get("net_worth", 0),
                    hero_damage=h.get("hero_damage", 0),
                    tower_damage=h.get("tower_damage", 0),
                    hero_healing=h.get("hero_healing", 0),
                    lane=h.get("lane_name"),
                    role=h.get("role"),
                    items=constants_fetcher.convert_item_ids_to_names(
                        [h.get(f"item_{i}") for i in range(6)]
                    ),
                    item_neutral=constants_fetcher.get_item_name(h.get("item_neutral")),
                )
                for h in heroes
                if h.get("team") == "dire"
            ]
            return MatchHeroesResponse(
                success=True,
                match_id=match_id,
                radiant_heroes=radiant_heroes,
                dire_heroes=dire_heroes,
            )
        return MatchHeroesResponse(
            success=False,
            match_id=match_id,
            error=f"Could not fetch heroes for match {match_id}",
        )

    @mcp.tool
    async def get_match_players(match_id: int) -> MatchPlayersResponse:
        """Get the 10 players in a Dota 2 match with their hero assignments."""
        heroes = await heroes_resource.get_match_heroes(match_id)
        if heroes:
            radiant = [
                MatchPlayerInfo(
                    player_name=h.get("player_name", ""),
                    pro_name=h.get("pro_name"),
                    account_id=h.get("account_id"),
                    hero_id=h.get("hero_id", 0),
                    hero_name=h.get("hero_name", ""),
                    localized_name=h.get("localized_name", ""),
                    position=h.get("position"),
                )
                for h in heroes
                if h.get("team") == "radiant"
            ]
            dire = [
                MatchPlayerInfo(
                    player_name=h.get("player_name", ""),
                    pro_name=h.get("pro_name"),
                    account_id=h.get("account_id"),
                    hero_id=h.get("hero_id", 0),
                    hero_name=h.get("hero_name", ""),
                    localized_name=h.get("localized_name", ""),
                    position=h.get("position"),
                )
                for h in heroes
                if h.get("team") == "dire"
            ]
            return MatchPlayersResponse(
                success=True, match_id=match_id, radiant=radiant, dire=dire
            )
        return MatchPlayersResponse(
            success=False,
            match_id=match_id,
            error=f"Could not fetch players for match {match_id}",
        )

    @mcp.tool
    async def get_hero_positions(
        match_id: int, minute: int, ctx: Optional[Context] = None
    ) -> HeroPositionsResponse:
        """Get hero positions at a specific minute in a Dota 2 match."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            positions = lane_service.get_hero_positions_at_minute(data, minute)
            pos_models = [
                HeroPosition(
                    hero=p.hero,
                    team=p.team,
                    x=round(p.x, 1),
                    y=round(p.y, 1),
                    game_time=p.game_time,
                )
                for p in positions
            ]
            return HeroPositionsResponse(
                success=True, match_id=match_id, minute=minute, positions=pos_models
            )
        except ValueError as e:
            return HeroPositionsResponse(
                success=False, match_id=match_id, minute=minute, error=str(e)
            )
        except Exception as e:
            return HeroPositionsResponse(
                success=False,
                match_id=match_id,
                minute=minute,
                error=f"Failed to get hero positions at minute {minute}: {e}",
            )

    @mcp.tool
    async def get_snapshot_at_time(
        match_id: int, game_time: float, ctx: Optional[Context] = None
    ) -> SnapshotAtTimeResponse:
        """Get game state snapshot at a specific game time."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            snapshot = seek_service.get_snapshot_at_time(data.replay_path, game_time)
            if not snapshot:
                return SnapshotAtTimeResponse(
                    success=False,
                    match_id=match_id,
                    error=f"Could not get snapshot at time {game_time}",
                )
            heroes = [
                HeroSnapshot(
                    hero=h.hero,
                    team=h.team,
                    player_id=h.player_id,
                    x=round(h.x, 1),
                    y=round(h.y, 1),
                    health=h.health,
                    max_health=h.max_health,
                    mana=h.mana,
                    max_mana=h.max_mana,
                    level=h.level,
                    alive=h.alive,
                )
                for h in snapshot.heroes
            ]
            return SnapshotAtTimeResponse(
                success=True,
                match_id=match_id,
                tick=snapshot.tick,
                game_time=snapshot.game_time,
                game_time_str=snapshot.game_time_str,
                radiant_gold=snapshot.radiant_gold,
                dire_gold=snapshot.dire_gold,
                heroes=heroes,
            )
        except ValueError as e:
            return SnapshotAtTimeResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return SnapshotAtTimeResponse(
                success=False, match_id=match_id, error=f"Failed to get snapshot: {e}"
            )
