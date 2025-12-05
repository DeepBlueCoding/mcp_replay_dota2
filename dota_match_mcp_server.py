#!/usr/bin/env python3
# ruff: noqa: E402
"""
Dota 2 Match MCP Server - Match-focused analysis

Provides MCP tools for analyzing specific Dota 2 matches using replay files.
All tools require a match_id and work with actual match data.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add project paths for imports
project_root = Path(__file__).parent.parent
mcp_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(mcp_dir))

from fastmcp import FastMCP, Context

# Create the MCP server instance
mcp = FastMCP("Dota 2 Match Analysis Server")

# Import business logic
from src.models.combat_log import (
    CombatLogFilters,
    CombatLogResponse,
    CourierKillsResponse,
    DownloadReplayResponse,
    FightCombatLogResponse,
    HeroDeathsResponse,
    ItemPurchasesResponse,
    ObjectiveKillsResponse,
    RunePickupsResponse,
)
from src.models.match_info import DraftResult, MatchInfoResult
from src.models.pro_scene import (
    LeagueMatchesResponse,
    LeaguesResponse,
    PlayerSearchResponse,
    ProMatchesResponse,
    ProPlayerResponse,
    TeamMatchesResponse,
    TeamResponse,
    TeamSearchResponse,
)
from src.resources.heroes_resources import heroes_resource
from src.resources.map_resources import get_cached_map_data
from src.resources.pro_scene_resources import pro_scene_resource
from src.utils.combat_log_parser import combat_log_parser
from src.utils.match_info_parser import match_info_parser
from src.utils.replay_cache import replay_cache
from src.utils.replay_downloader import ReplayDownloader
from src.services.replay.replay_service import ReplayService
from src.services.cache.replay_cache import ReplayCache as ReplayCacheV2

# Initialize v2 services (for new tools with progress reporting)
_replay_cache_v2 = ReplayCacheV2()
_replay_service = ReplayService(cache=_replay_cache_v2)

# Phase 2: Combat and Fight services
from src.services.combat.combat_service import CombatService
from src.services.combat.fight_service import FightService
_combat_service = CombatService()
_fight_service = FightService(combat_service=_combat_service)

# Phase 3: Jungle and Lane services
from src.services.jungle.jungle_service import JungleService
from src.services.lane.lane_service import LaneService
_jungle_service = JungleService()
_lane_service = LaneService()

# Phase 4: Dense Seek services
from src.services.seek.seek_service import SeekService
_seek_service = SeekService()

from src.utils.timeline_parser import timeline_parser

# Purge expired replay cache entries on server start
_expired_count = replay_cache.clear_expired()
if _expired_count > 0:
    import logging
    logging.getLogger(__name__).info(f"Purged {_expired_count} expired replay cache entries")


# Define MCP Resources
@mcp.resource(
    "dota2://heroes/all",
    name="All Dota 2 Heroes",
    description="Complete list of all Dota 2 heroes with their canonical names, aliases, and attributes",
    mime_type="application/json"
)
async def all_heroes_resource() -> Dict[str, Dict[str, Any]]:
    """
    MCP resource that provides all Dota 2 heroes data.

    Returns:
        Complete heroes data in the same format as heroes.json
    """
    return await heroes_resource.get_all_heroes()


@mcp.resource(
    "dota2://map",
    name="Dota 2 Map Data",
    description="Complete Dota 2 map: towers, neutral camps, runes, Roshan, outposts, shops, landmarks",
    mime_type="application/json"
)
async def map_data_resource() -> Dict[str, Any]:
    """
    MCP resource providing static Dota 2 map data.

    Includes:
    - Towers: All 22 towers with team, tier, lane, and position
    - Barracks: All 12 barracks with team, lane, type (melee/ranged)
    - Ancients: Both team ancients
    - Neutral camps: All jungle camps with tier (small/medium/large/ancient)
    - Rune spawns: Power, bounty, wisdom, and water runes
    - Outposts: Both outpost locations
    - Shops: Base, secret, and side shops
    - Landmarks: Roshan pit, fountains, shrines, tormentors, high ground

    Coordinate system:
    - Origin (0,0) is approximately center of map
    - Radiant base is bottom-left (negative X, negative Y)
    - Dire base is top-right (positive X, positive Y)
    - Map spans roughly -8000 to +8000 in both axes

    Returns:
        Complete map data with all positions
    """
    map_data = get_cached_map_data()
    return map_data.model_dump()




@mcp.resource(
    "dota2://pro/players",
    name="Pro Players",
    description="All professional Dota 2 players with names, teams, and aliases",
    mime_type="application/json"
)
async def pro_players_resource() -> Dict[str, Any]:
    """
    MCP resource providing all professional players.

    Returns a list of pro players with:
    - account_id: Steam account ID
    - name: Professional name
    - personaname: Steam persona name
    - team_id, team_name, team_tag: Current team info
    - country_code: Player nationality
    - fantasy_role: 1=Core, 2=Support
    - is_locked: Whether player is locked (retired/inactive)
    - is_pro: Whether considered a pro player

    Returns:
        Dictionary with list of pro players
    """
    players = await pro_scene_resource.get_all_players()
    return {
        "total_players": len(players),
        "players": players,
    }


@mcp.resource(
    "dota2://pro/teams",
    name="Pro Teams",
    description="All professional Dota 2 teams with ratings and win/loss records",
    mime_type="application/json"
)
async def pro_teams_resource() -> Dict[str, Any]:
    """
    MCP resource providing all professional teams.

    Returns a list of teams with:
    - team_id: Team ID
    - name: Team name
    - tag: Team tag/abbreviation
    - rating: Team ELO rating
    - wins, losses: Overall record
    - last_match_time: Unix timestamp of last match
    - logo_url: Team logo URL

    Returns:
        Dictionary with list of teams
    """
    teams = await pro_scene_resource.get_all_teams()
    return {
        "total_teams": len(teams),
        "teams": teams,
    }




# Define MCP Tools
@mcp.tool
async def download_replay(match_id: int, ctx: Context) -> DownloadReplayResponse:
    """
    Download and cache the replay file for a Dota 2 match.

    Use this tool FIRST before asking analysis questions about a match.
    Replay files are large (50-400MB) and can take 1-5 minutes to download.

    Once downloaded, the replay is cached locally and subsequent queries
    for the same match will be instant.

    Progress is reported during download:
    - 0-10%: Checking cache and getting replay URL
    - 10-40%: Downloading compressed file
    - 40-50%: Extracting replay
    - 50-95%: Parsing replay (uses python-manta v2)
    - 95-100%: Caching results

    Args:
        match_id: The Dota 2 match ID (from OpenDota, Dotabuff, or in-game)

    Returns:
        DownloadReplayResponse with success status and file info
    """
    # Create progress callback that reports to MCP client
    async def progress_callback(current: int, total: int, message: str) -> None:
        await ctx.report_progress(current, total)

    # Check if already downloaded (fast path)
    if _replay_service.is_downloaded(match_id):
        file_size_mb = _replay_service.get_replay_file_size(match_id)
        await ctx.report_progress(100, 100)
        return DownloadReplayResponse(
            success=True,
            match_id=match_id,
            replay_path=str(_replay_service._replay_dir / f"{match_id}.dem"),
            file_size_mb=round(file_size_mb or 0, 1),
            already_cached=True,
        )

    try:
        # Download with progress reporting
        replay_path = await _replay_service.download_only(match_id, progress=progress_callback)

        file_size_mb = replay_path.stat().st_size / (1024 * 1024)
        return DownloadReplayResponse(
            success=True,
            match_id=match_id,
            replay_path=str(replay_path),
            file_size_mb=round(file_size_mb, 1),
            already_cached=False,
        )

    except ValueError as e:
        return DownloadReplayResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )
    except Exception as e:
        return DownloadReplayResponse(
            success=False,
            match_id=match_id,
            error=f"Could not download replay: {e}",
        )


@mcp.tool
async def get_match_timeline(match_id: int) -> Dict[str, Any]:
    """
    Get time-series data for a Dota 2 match.

    Returns per-player timeline data:
    - net_worth: Array of net worth values (sampled every 30 seconds)
    - hero_damage: Array of cumulative hero damage
    - kda_timeline: Array of {game_time, kills, deaths, assists, level} snapshots

    Also returns team-level graphs for experience and gold.

    Data is extracted from the replay file metadata.

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with timeline data for all players and teams
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not download replay for this match"
        }

    timeline = timeline_parser.parse_timeline(replay_path)
    if not timeline:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not parse timeline from replay"
        }

    return {
        "success": True,
        **timeline
    }


@mcp.tool
async def get_stats_at_minute(match_id: int, minute: int) -> Dict[str, Any]:
    """
    Get player stats at a specific minute in a Dota 2 match.

    Returns per-player stats:
    - net_worth: Net worth at that minute
    - hero_damage: Cumulative hero damage at that minute
    - kills, deaths, assists: KDA at that minute
    - level: Hero level at that minute

    Args:
        match_id: The Dota 2 match ID
        minute: Game minute to get stats for (0-based)

    Returns:
        Dictionary with per-player stats at the specified minute
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not download replay for this match"
        }

    timeline = timeline_parser.parse_timeline(replay_path)
    if not timeline:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not parse timeline from replay"
        }

    stats = timeline_parser.get_stats_at_minute(timeline, minute)
    return {
        "success": True,
        "match_id": match_id,
        **stats
    }


@mcp.tool
async def get_hero_deaths(match_id: int) -> HeroDeathsResponse:
    """
    Get all hero deaths in a Dota 2 match.

    Returns a list of hero death events with:
    - game_time: Seconds since game start
    - game_time_str: Formatted as M:SS
    - killer: Hero or unit that got the kill
    - victim: Hero that died
    - killer_is_hero: Whether the killer was a hero
    - ability: Ability or item that dealt the killing blow (if available)

    Args:
        match_id: The Dota 2 match ID

    Returns:
        HeroDeathsResponse with list of hero death events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return HeroDeathsResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    deaths = combat_log_parser.get_hero_deaths(replay_path)

    return HeroDeathsResponse(
        success=True,
        match_id=match_id,
        total_deaths=len(deaths),
        deaths=deaths,
    )


@mcp.tool
async def get_combat_log(
    match_id: int,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    hero_filter: Optional[str] = None,
) -> CombatLogResponse:
    """
    Get combat log events from a Dota 2 match with optional filters.

    Returns combat events including damage, abilities, modifiers (buffs/debuffs), and deaths.

    Each event contains:
    - type: DAMAGE, MODIFIER_ADD, ABILITY, DEATH, etc.
    - game_time: Seconds since game start
    - game_time_str: Formatted as M:SS
    - attacker: Source of the event (hero name without prefix)
    - attacker_is_hero: Whether attacker is a hero
    - target: Target of the event
    - target_is_hero: Whether target is a hero
    - ability: Ability or item involved (if any)
    - value: Damage amount or other numeric value

    Args:
        match_id: The Dota 2 match ID
        start_time: Filter events after this game time in seconds (optional)
        end_time: Filter events before this game time in seconds (optional)
        hero_filter: Only include events involving this hero, e.g. "earthshaker" (optional)

    Returns:
        CombatLogResponse with list of combat log events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return CombatLogResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    events = combat_log_parser.get_combat_log(
        replay_path,
        start_time=start_time,
        end_time=end_time,
        hero_filter=hero_filter,
    )

    return CombatLogResponse(
        success=True,
        match_id=match_id,
        total_events=len(events),
        filters=CombatLogFilters(
            start_time=start_time,
            end_time=end_time,
            hero_filter=hero_filter,
        ),
        events=events,
    )


@mcp.tool
async def get_fight_combat_log(
    match_id: int,
    reference_time: float,
    hero: Optional[str] = None,
) -> FightCombatLogResponse:
    """
    Get combat log for a fight leading up to a specific moment (e.g., a death).

    Automatically detects fight boundaries by analyzing combat activity and participant
    connectivity. Separate skirmishes happening simultaneously in different lanes are
    correctly identified as distinct fights.

    Use this after get_hero_deaths to get the full combat narrative for a kill,
    or use it to get all combat events around a specific game time (e.g., team fight at minute 11).

    Args:
        match_id: The Dota 2 match ID
        reference_time: Reference game time in seconds (e.g., death time from get_hero_deaths)
        hero: Optional hero name to anchor fight detection, e.g. "earthshaker".
              If omitted, finds the fight closest to reference_time.

    Returns:
        FightCombatLogResponse with fight boundaries, participants, and combat events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return FightCombatLogResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    result = combat_log_parser.get_combat_timespan(
        replay_path,
        reference_time=reference_time,
        hero=hero,
    )

    return FightCombatLogResponse(
        success=True,
        match_id=match_id,
        hero=hero,
        fight_start=result.fight_start,
        fight_start_str=result.fight_start_str,
        fight_end=result.fight_end,
        fight_end_str=result.fight_end_str,
        duration=result.duration,
        participants=result.participants,
        total_events=result.total_events,
        events=result.events,
    )


@mcp.tool
async def get_item_purchases(
    match_id: int,
    hero_filter: Optional[str] = None,
) -> ItemPurchasesResponse:
    """
    Get item purchase timings for heroes in a Dota 2 match.

    Returns a chronological list of item purchases with:
    - game_time: Seconds since game start (can be negative for pre-horn purchases)
    - game_time_str: Formatted as M:SS
    - hero: Hero that purchased the item
    - item: Item name (e.g., "item_bfury", "item_power_treads")

    Use this to answer questions like:
    - "When did Juggernaut finish Battlefury?"
    - "What was Anti-Mage's item progression?"
    - "Who bought the first BKB?"

    Args:
        match_id: The Dota 2 match ID
        hero_filter: Only include purchases by this hero, e.g. "juggernaut" (optional)

    Returns:
        ItemPurchasesResponse with list of item purchase events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return ItemPurchasesResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    purchases = combat_log_parser.get_item_purchases(
        replay_path,
        hero_filter=hero_filter,
    )

    return ItemPurchasesResponse(
        success=True,
        match_id=match_id,
        hero_filter=hero_filter,
        total_purchases=len(purchases),
        purchases=purchases,
    )


@mcp.tool
async def get_courier_kills(match_id: int) -> CourierKillsResponse:
    """
    Get all courier kills in a Dota 2 match.

    Returns a list of courier kill events with:
    - game_time: Seconds since game start
    - game_time_str: Formatted as M:SS
    - killer: Hero that killed the courier
    - killer_is_hero: Whether the killer was a hero
    - team: Team whose courier was killed (radiant/dire)

    Args:
        match_id: The Dota 2 match ID

    Returns:
        CourierKillsResponse with list of courier kill events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return CourierKillsResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    kills = combat_log_parser.get_courier_kills(replay_path)

    return CourierKillsResponse(
        success=True,
        match_id=match_id,
        total_kills=len(kills),
        kills=kills,
    )


@mcp.tool
async def get_objective_kills(match_id: int) -> ObjectiveKillsResponse:
    """
    Get all major objective kills in a Dota 2 match.

    Returns kills of:
    - Roshan: game_time, killer, team, kill_number (1st, 2nd, 3rd Roshan)
    - Tormentor: game_time, killer, team, side (which Tormentor was killed)
    - Towers: game_time, tower name, team, tier, lane, killer
    - Barracks: game_time, barracks name, team, lane, type (melee/ranged), killer

    Use this to analyze:
    - When did each team take Roshan?
    - Tower trade patterns and timing
    - High ground pushes and barracks destruction
    - Tormentor control

    Args:
        match_id: The Dota 2 match ID

    Returns:
        ObjectiveKillsResponse with all objective kill events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return ObjectiveKillsResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    roshan, tormentor, towers, barracks = combat_log_parser.get_objective_kills(replay_path)

    return ObjectiveKillsResponse(
        success=True,
        match_id=match_id,
        roshan_kills=roshan,
        tormentor_kills=tormentor,
        tower_kills=towers,
        barracks_kills=barracks,
    )


@mcp.tool
async def get_rune_pickups(match_id: int) -> RunePickupsResponse:
    """
    Get power rune pickups in a Dota 2 match.

    Returns a list of power rune pickup events with:
    - game_time: Seconds since game start
    - game_time_str: Formatted as M:SS
    - hero: Hero that picked up the rune
    - rune_type: Type of rune (haste, double_damage, arcane, invisibility, regeneration, shield)

    Note: Only power runes are trackable. Bounty, wisdom, and water runes
    don't leave detectable events in the replay data.

    Use this to answer questions like:
    - "Who got the most power runes?"
    - "What runes did the mid player secure?"
    - "When did they get a DD rune before fighting?"

    Args:
        match_id: The Dota 2 match ID

    Returns:
        RunePickupsResponse with list of power rune pickup events
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return RunePickupsResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay for this match"
        )

    pickups = combat_log_parser.get_rune_pickups(replay_path)

    return RunePickupsResponse(
        success=True,
        match_id=match_id,
        total_pickups=len(pickups),
        pickups=pickups,
    )


@mcp.tool
async def get_match_draft(match_id: int) -> Dict[str, Any]:
    """
    Get the complete draft (picks and bans) for a Dota 2 match.

    Returns the full draft sequence in order, preserving the exact pick/ban order
    as it happened in Captain's Mode or other draft modes.

    Each draft action contains:
    - order: Draft sequence number (1-24 for CM)
    - is_pick: True if pick, False if ban
    - team: "radiant" or "dire"
    - hero_id: Numeric hero ID
    - hero_name: Internal hero name (e.g., "juggernaut")
    - localized_name: Display name (e.g., "Juggernaut")

    Also provides convenience lists for radiant/dire picks and bans separately.

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with draft actions and convenience lists by team
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not download replay for this match"
        }

    draft = match_info_parser.get_draft(replay_path)
    if not draft:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not parse draft from replay"
        }

    return {
        "success": True,
        **draft.model_dump()
    }


@mcp.tool
async def get_match_info(match_id: int) -> Dict[str, Any]:
    """
    Get match metadata and player information for a Dota 2 match.

    Returns comprehensive match information including:
    - Match metadata: match_id, game_mode, winner, duration
    - Pro match data: is_pro_match, league_id
    - Team info: team_id, team_tag, team_name for both Radiant and Dire
    - Player info: player_name, hero, team, steam_id for all 10 players

    This is particularly useful for professional matches where it provides
    team names, player names, and league information.

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with match metadata, teams, and players
    """
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not download replay for this match"
        }

    match_info = match_info_parser.get_match_info(replay_path)
    if not match_info:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not parse match info from replay"
        }

    return {
        "success": True,
        **match_info.model_dump()
    }


@mcp.tool
async def get_match_heroes(match_id: int) -> Dict[str, Any]:
    """
    Get the 10 heroes in a Dota 2 match with detailed stats.

    Returns per-hero:
    - Hero: hero_id, hero_name, localized_name, primary_attr, attack_type, roles
    - Performance: kills, deaths, assists, last_hits, GPM, XPM, net_worth, hero_damage
    - Position: team (radiant/dire), lane, role (core/support)
    - Items: item_0 through item_5, item_neutral
    - Player: player_name, pro_name (who is controlling this hero)

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with radiant and dire team heroes
    """
    heroes = await heroes_resource.get_match_heroes(match_id)
    if heroes:
        radiant = [h for h in heroes if h.get("team") == "radiant"]
        dire = [h for h in heroes if h.get("team") == "dire"]
        return {
            "success": True,
            "match_id": match_id,
            "radiant": radiant,
            "dire": dire,
        }
    return {
        "success": False,
        "match_id": match_id,
        "error": f"Could not fetch heroes for match {match_id}"
    }


@mcp.tool
async def get_match_players(match_id: int) -> Dict[str, Any]:
    """
    Get the 10 players in a Dota 2 match with their hero assignments.

    Returns per-player:
    - Player: player_name (Steam name), pro_name (professional name if known), account_id
    - Team: radiant or dire
    - Hero: hero_id, hero_name, localized_name

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with radiant and dire team players
    """
    heroes = await heroes_resource.get_match_heroes(match_id)
    if heroes:
        players = []
        for h in heroes:
            players.append({
                "player_name": h.get("player_name"),
                "pro_name": h.get("pro_name"),
                "account_id": h.get("account_id"),
                "team": h.get("team"),
                "hero_id": h.get("hero_id"),
                "hero_name": h.get("hero_name"),
                "localized_name": h.get("localized_name"),
            })
        radiant = [p for p in players if p.get("team") == "radiant"]
        dire = [p for p in players if p.get("team") == "dire"]
        return {
            "success": True,
            "match_id": match_id,
            "radiant": radiant,
            "dire": dire,
        }
    return {
        "success": False,
        "match_id": match_id,
        "error": f"Could not fetch players for match {match_id}"
    }


# Pro Scene Tools
@mcp.tool
async def search_pro_player(
    query: str,
    max_results: int = 10,
) -> PlayerSearchResponse:
    """
    Search for professional Dota 2 players by name or alias.

    Supports fuzzy matching, so you can search for:
    - Pro names: "yatoro", "collapse", "miposhka"
    - Steam names: "raddan" (Yatoro's old name)
    - Partial names: "toro" will match "yatoro"

    Returns a list of matches with similarity scores.

    Args:
        query: Search string (player name, alias, etc.)
        max_results: Maximum number of results to return (default: 10)

    Returns:
        PlayerSearchResponse with matching players sorted by relevance
    """
    return await pro_scene_resource.search_player(query, max_results=max_results)


@mcp.tool
async def search_team(
    query: str,
    max_results: int = 10,
) -> TeamSearchResponse:
    """
    Search for professional Dota 2 teams by name, tag, or alias.

    Supports fuzzy matching, so you can search for:
    - Full names: "Team Spirit", "Evil Geniuses"
    - Tags: "TS", "EG", "OG"
    - Partial names: "spirit" will match "Team Spirit"
    - Aliases: "secret" will match "Team Secret"

    Returns a list of matches with similarity scores.

    Args:
        query: Search string (team name, tag, alias, etc.)
        max_results: Maximum number of results to return (default: 10)

    Returns:
        TeamSearchResponse with matching teams sorted by relevance
    """
    return await pro_scene_resource.search_team(query, max_results=max_results)


@mcp.tool
async def get_pro_player(account_id: int) -> ProPlayerResponse:
    """
    Get detailed information about a professional player by account ID.

    Returns player details including:
    - Professional name and Steam persona name
    - Current team information
    - Country/nationality
    - Fantasy role (Core/Support)
    - Known aliases

    Use search_pro_player first if you don't know the account ID.

    Args:
        account_id: Player's Steam account ID

    Returns:
        ProPlayerResponse with player details
    """
    return await pro_scene_resource.get_player(account_id)


@mcp.tool
async def get_pro_player_by_name(name: str) -> ProPlayerResponse:
    """
    Get detailed information about a professional player by name.

    Combines fuzzy search and player lookup in one call.
    Use this when you know the player's name but not their account ID.

    Args:
        name: Player name to search for (supports fuzzy matching)

    Returns:
        ProPlayerResponse with player details of best match
    """
    return await pro_scene_resource.get_player_by_name(name)


@mcp.tool
async def get_team(team_id: int) -> TeamResponse:
    """
    Get detailed information about a team by ID.

    Returns team details including:
    - Team name, tag, logo
    - Rating (ELO)
    - Win/loss record
    - Current roster (players with games played on this team)
    - Known aliases

    Use search_team first if you don't know the team ID.

    Args:
        team_id: Team ID

    Returns:
        TeamResponse with team details and roster
    """
    return await pro_scene_resource.get_team(team_id)


@mcp.tool
async def get_team_by_name(name: str) -> TeamResponse:
    """
    Get detailed information about a team by name.

    Combines fuzzy search and team lookup in one call.
    Use this when you know the team's name but not their ID.

    Args:
        name: Team name to search for (supports fuzzy matching)

    Returns:
        TeamResponse with team details and roster of best match
    """
    return await pro_scene_resource.get_team_by_name(name)


@mcp.tool
async def get_team_matches(
    team_id: int,
    limit: int = 50,
) -> TeamMatchesResponse:
    """
    Get recent matches for a team.

    Returns match summaries including:
    - Match ID (can be used with other tools for detailed analysis)
    - Teams: radiant/dire team names and IDs
    - Result: radiant_win, duration
    - Tournament: league_id, league_name
    - Timestamp: start_time

    Args:
        team_id: Team ID
        limit: Maximum number of matches to return (default: 50)

    Returns:
        TeamMatchesResponse with list of recent matches
    """
    return await pro_scene_resource.get_team_matches(team_id, limit=limit)


@mcp.tool
async def get_leagues(tier: Optional[str] = None) -> LeaguesResponse:
    """
    Get all Dota 2 leagues/tournaments.

    Returns league information including:
    - league_id: Can be used to filter team matches
    - name: League/tournament name
    - tier: premium, professional, amateur

    Args:
        tier: Filter by tier (optional): "premium", "professional", "amateur"

    Returns:
        LeaguesResponse with list of leagues
    """
    return await pro_scene_resource.get_leagues(tier=tier)


@mcp.tool
async def get_pro_matches(limit: int = 100) -> ProMatchesResponse:
    """
    Get recent professional Dota 2 matches with series grouping.

    Returns both individual matches and series summaries:

    **Matches** include:
    - match_id: Can be used with other tools for detailed analysis
    - Teams: radiant/dire team names and IDs
    - Score: radiant_score, dire_score (kills)
    - Result: radiant_win, duration
    - Tournament: league_id, league_name
    - Series: series_id, series_type, game_number (1, 2, 3...)

    **Series** include:
    - series_id: Groups related matches
    - series_type_name: "Bo1", "Bo3", "Bo5"
    - Teams: team1/team2 names and IDs
    - Score: team1_wins, team2_wins
    - Winner: winner_id, winner_name (if complete)
    - games: List of matches in the series with game_number

    Use this to answer questions like:
    - "What pro matches happened recently?"
    - "Show me the latest Team Spirit vs OG series"
    - "What was the score in that Bo3?"

    Args:
        limit: Maximum matches to return (default: 100)

    Returns:
        ProMatchesResponse with matches and series
    """
    return await pro_scene_resource.get_pro_matches(limit=limit)


@mcp.tool
async def get_league_matches(
    league_id: int,
    limit: int = 100,
) -> LeagueMatchesResponse:
    """
    Get matches from a specific league/tournament with series grouping.

    Returns all matches from a tournament, grouped into series.
    Use get_leagues to find league_ids.

    **Matches** include:
    - match_id: Can be used with other tools for detailed analysis
    - Teams: radiant/dire team names and IDs
    - Score: radiant_score, dire_score (kills)
    - Result: radiant_win, duration
    - Series: series_id, series_type, game_number

    **Series** include:
    - series_type_name: "Bo1", "Bo3", "Bo5"
    - Teams: team1/team2 names and win counts
    - Winner: winner_id, winner_name (if complete)
    - games: Ordered list of matches with game numbers

    Use this to answer questions like:
    - "Show me all matches from TI12"
    - "What was the grand final series at DreamLeague?"
    - "Who won the most series at ESL One?"

    Args:
        league_id: League/tournament ID (get from get_leagues)
        limit: Maximum matches to return (default: 100)

    Returns:
        LeagueMatchesResponse with matches and series from the tournament
    """
    return await pro_scene_resource.get_league_matches(league_id, limit=limit)


# Phase 2: Fight Analysis Tools (v2 services)
@mcp.tool
async def list_fights(match_id: int, ctx: Context) -> Dict[str, Any]:
    """
    List all fights in a Dota 2 match.

    A fight is defined as a group of hero deaths occurring within 15 seconds of each other.
    Fights are categorized as:
    - Teamfights: 3+ deaths
    - Skirmishes: 1-2 deaths

    Returns:
    - total_fights: Number of distinct fights
    - teamfights: Number of teamfights (3+ deaths)
    - skirmishes: Number of smaller engagements
    - total_deaths: Total hero deaths in the match
    - fights: List of fights with start_time, deaths, participants

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with fight summary and list of all fights
    """
    # Create progress callback
    async def progress_callback(current: int, total: int, message: str) -> None:
        await ctx.report_progress(current, total)

    try:
        # Get parsed data (cached or download+parse)
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        # Get fight summary
        summary = _fight_service.get_fight_summary(data)

        return {
            "success": True,
            "match_id": match_id,
            **summary,
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to analyze fights: {e}",
        }


@mcp.tool
async def get_teamfights(
    match_id: int,
    min_deaths: int = 3,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get only teamfights from a Dota 2 match.

    Teamfights are fights with 3 or more hero deaths.
    Use min_deaths parameter to adjust the threshold.

    Returns for each teamfight:
    - fight_id: Unique identifier
    - start_time: When the fight started (M:SS format)
    - duration: How long the fight lasted
    - deaths: List of hero deaths with killer, victim, time
    - participants: All heroes involved

    Args:
        match_id: The Dota 2 match ID
        min_deaths: Minimum deaths to classify as teamfight (default: 3)

    Returns:
        Dictionary with list of teamfights
    """
    # Create progress callback
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        teamfights = _fight_service.get_teamfights(data, min_deaths=min_deaths)

        return {
            "success": True,
            "match_id": match_id,
            "min_deaths_threshold": min_deaths,
            "total_teamfights": len(teamfights),
            "teamfights": [
                {
                    "fight_id": f.fight_id,
                    "start_time": f.start_time_str,
                    "end_time": f.end_time_str,
                    "duration_seconds": round(f.duration, 1),
                    "total_deaths": f.total_deaths,
                    "participants": f.participants,
                    "deaths": [
                        {
                            "game_time": d.game_time_str,
                            "killer": d.killer,
                            "victim": d.victim,
                            "ability": d.ability,
                        }
                        for d in f.deaths
                    ],
                }
                for f in teamfights
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get teamfights: {e}",
        }


@mcp.tool
async def get_fight(
    match_id: int,
    fight_id: str,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific fight.

    Use list_fights first to get available fight_ids.

    Returns:
    - Fight timing (start, end, duration)
    - All participants
    - All deaths with killer, victim, ability, position
    - Damage breakdown (if available)

    Args:
        match_id: The Dota 2 match ID
        fight_id: Fight identifier (e.g., "fight_1", "fight_5")

    Returns:
        Detailed fight information
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        fight = _fight_service.get_fight_by_id(data, fight_id)

        if not fight:
            return {
                "success": False,
                "match_id": match_id,
                "error": f"Fight '{fight_id}' not found. Use list_fights to see available fights.",
            }

        return {
            "success": True,
            "match_id": match_id,
            "fight_id": fight.fight_id,
            "start_time": fight.start_time_str,
            "start_time_seconds": fight.start_time,
            "end_time": fight.end_time_str,
            "end_time_seconds": fight.end_time,
            "duration_seconds": round(fight.duration, 1),
            "is_teamfight": fight.is_teamfight,
            "total_deaths": fight.total_deaths,
            "participants": fight.participants,
            "deaths": [
                {
                    "game_time": d.game_time_str,
                    "game_time_seconds": d.game_time,
                    "killer": d.killer,
                    "killer_is_hero": d.killer_is_hero,
                    "victim": d.victim,
                    "ability": d.ability,
                    "position_x": d.position_x,
                    "position_y": d.position_y,
                }
                for d in fight.deaths
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }


# Phase 3: Jungle and Lane Analysis Tools (v2 services)
@mcp.tool
async def get_camp_stacks(
    match_id: int,
    hero_filter: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get all neutral camp stacks in a Dota 2 match.

    Camp stacks are detected from the combat log using the native NEUTRAL_CAMP_STACK event.

    Returns:
    - total_stacks: Number of stacks in the match
    - stacks: List of stack events with:
      - game_time: When the stack occurred (M:SS format)
      - stacker: Hero that created the stack
      - camp_type: Type of camp (ancient, large, medium, small) if detectable
      - stack_count: Number of creeps in the stack

    Args:
        match_id: The Dota 2 match ID
        hero_filter: Only show stacks by this hero (optional)

    Returns:
        Dictionary with camp stack events
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        stacks = _jungle_service.get_camp_stacks(data, hero_filter=hero_filter)

        return {
            "success": True,
            "match_id": match_id,
            "hero_filter": hero_filter,
            "total_stacks": len(stacks),
            "stacks": [
                {
                    "game_time": s.game_time_str,
                    "game_time_seconds": s.game_time,
                    "stacker": s.stacker,
                    "camp_type": s.camp_type,
                    "stack_count": s.stack_count,
                }
                for s in stacks
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get camp stacks: {e}",
        }


@mcp.tool
async def get_jungle_summary(match_id: int, ctx: Context = None) -> Dict[str, Any]:
    """
    Get jungle activity summary for a Dota 2 match.

    Provides an overview of neutral camp stacking and efficiency.

    Returns:
    - total_stacks: Total camp stacks in the match
    - stacks_by_hero: Dictionary mapping hero name to stack count
    - stack_efficiency: Dictionary mapping hero to stacks per 10 minutes

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with jungle summary
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        summary = _jungle_service.get_jungle_summary(data)
        efficiency = _jungle_service.get_stack_efficiency(data)

        return {
            "success": True,
            "match_id": match_id,
            "total_stacks": summary.total_stacks,
            "stacks_by_hero": summary.stacks_by_hero,
            "stack_efficiency_per_10min": efficiency,
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get jungle summary: {e}",
        }


@mcp.tool
async def get_lane_summary(match_id: int, ctx: Context = None) -> Dict[str, Any]:
    """
    Get laning phase summary for a Dota 2 match.

    Analyzes the first 10 minutes (laning phase) to determine:
    - Lane winners (based on CS advantage)
    - Per-hero laning stats
    - Overall laning score by team

    Returns:
    - lane_winners: Winner of each lane (radiant/dire/even)
      - top: Winner of top lane
      - mid: Winner of mid lane
      - bot: Winner of bot lane
    - team_scores: Overall laning score by team
    - hero_stats: Per-hero laning stats including:
      - hero: Hero name
      - lane: Which lane (top/mid/bot)
      - role: Role (core/offlane/mid/support)
      - team: radiant/dire
      - last_hits_5min, last_hits_10min: CS at 5 and 10 minutes
      - denies_5min, denies_10min: Denies at 5 and 10 minutes
      - gold_5min, gold_10min: Net worth at 5 and 10 minutes
      - level_5min, level_10min: Level at 5 and 10 minutes

    Args:
        match_id: The Dota 2 match ID

    Returns:
        Dictionary with laning phase summary
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        summary = _lane_service.get_lane_summary(data)

        return {
            "success": True,
            "match_id": match_id,
            "lane_winners": {
                "top": summary.top_winner,
                "mid": summary.mid_winner,
                "bot": summary.bot_winner,
            },
            "team_scores": {
                "radiant": round(summary.radiant_laning_score, 1),
                "dire": round(summary.dire_laning_score, 1),
            },
            "hero_stats": [
                {
                    "hero": s.hero,
                    "lane": s.lane,
                    "role": s.role,
                    "team": s.team,
                    "last_hits_5min": s.last_hits_5min,
                    "last_hits_10min": s.last_hits_10min,
                    "denies_5min": s.denies_5min,
                    "denies_10min": s.denies_10min,
                    "gold_5min": s.gold_5min,
                    "gold_10min": s.gold_10min,
                    "level_5min": s.level_5min,
                    "level_10min": s.level_10min,
                }
                for s in summary.hero_stats
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get lane summary: {e}",
        }


@mcp.tool
async def get_cs_at_minute(
    match_id: int,
    minute: int,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get last hits, denies, gold, and level for all heroes at a specific minute.

    Useful for tracking CS progression and comparing farm at key timings.

    Args:
        match_id: The Dota 2 match ID
        minute: Game minute to query (e.g., 5, 10, 15)

    Returns:
        Dictionary with CS data for all heroes at the specified minute
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        cs_data = _lane_service.get_cs_at_minute(data, minute)

        return {
            "success": True,
            "match_id": match_id,
            "minute": minute,
            "heroes": cs_data,
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get CS at minute {minute}: {e}",
        }


@mcp.tool
async def get_hero_positions(
    match_id: int,
    minute: int,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get hero positions at a specific minute in a Dota 2 match.

    Returns X,Y coordinates for all 10 heroes at the specified game minute.
    Useful for understanding lane assignments and rotations.

    Args:
        match_id: The Dota 2 match ID
        minute: Game minute to query (e.g., 0, 5, 10)

    Returns:
        Dictionary with hero positions at the specified minute
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        positions = _lane_service.get_hero_positions_at_minute(data, minute)

        return {
            "success": True,
            "match_id": match_id,
            "minute": minute,
            "positions": [
                {
                    "hero": p.hero,
                    "team": p.team,
                    "x": round(p.x, 1),
                    "y": round(p.y, 1),
                    "game_time": p.game_time,
                }
                for p in positions
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get hero positions at minute {minute}: {e}",
        }


# Phase 4: Dense Seek Tools (v2 services)
@mcp.tool
async def get_snapshot_at_time(
    match_id: int,
    game_time: float,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get game state snapshot at a specific game time.

    Returns high-resolution state including all hero positions, health, mana, and levels.
    Uses python-manta v2's tick-level seeking for precise snapshots.

    Args:
        match_id: The Dota 2 match ID
        game_time: Game time in seconds (e.g., 300.0 for 5:00)

    Returns:
        Dictionary with game state at the specified time
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        # First ensure replay is downloaded
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        # Get snapshot using SeekService
        snapshot = _seek_service.get_snapshot_at_time(data.replay_path, game_time)

        if not snapshot:
            return {
                "success": False,
                "match_id": match_id,
                "error": f"Could not get snapshot at time {game_time}",
            }

        return {
            "success": True,
            "match_id": match_id,
            "tick": snapshot.tick,
            "game_time": snapshot.game_time,
            "game_time_str": snapshot.game_time_str,
            "radiant_gold": snapshot.radiant_gold,
            "dire_gold": snapshot.dire_gold,
            "heroes": [
                {
                    "hero": h.hero,
                    "team": h.team,
                    "player_id": h.player_id,
                    "x": round(h.x, 1),
                    "y": round(h.y, 1),
                    "health": h.health,
                    "max_health": h.max_health,
                    "mana": h.mana,
                    "max_mana": h.max_mana,
                    "level": h.level,
                    "alive": h.alive,
                }
                for h in snapshot.heroes
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get snapshot: {e}",
        }


@mcp.tool
async def get_position_timeline(
    match_id: int,
    start_time: float,
    end_time: float,
    hero_filter: Optional[str] = None,
    interval_seconds: float = 1.0,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get hero positions over a time range at regular intervals.

    Useful for tracking hero movement patterns, rotations, and positioning.

    Args:
        match_id: The Dota 2 match ID
        start_time: Start time in seconds (e.g., 300.0 for 5:00)
        end_time: End time in seconds (e.g., 360.0 for 6:00)
        hero_filter: Only include this hero (optional)
        interval_seconds: Sampling interval in seconds (default 1.0)

    Returns:
        Dictionary with position timelines for each hero
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        timelines = _seek_service.get_position_timeline(
            replay_path=data.replay_path,
            start_time=start_time,
            end_time=end_time,
            hero_filter=hero_filter,
            interval_seconds=interval_seconds,
        )

        return {
            "success": True,
            "match_id": match_id,
            "start_time": start_time,
            "end_time": end_time,
            "interval_seconds": interval_seconds,
            "hero_filter": hero_filter,
            "heroes": [
                {
                    "hero": t.hero,
                    "team": t.team,
                    "positions": [
                        {
                            "tick": p[0],
                            "game_time": round(p[1], 1),
                            "x": round(p[2], 1),
                            "y": round(p[3], 1),
                        }
                        for p in t.positions
                    ],
                }
                for t in timelines
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get position timeline: {e}",
        }


@mcp.tool
async def get_fight_replay(
    match_id: int,
    start_time: float,
    end_time: float,
    interval_seconds: float = 0.5,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Get high-resolution replay data for a fight.

    Samples game state at regular intervals during the fight to show
    how hero positions, health, and mana changed throughout.

    Use get_fight to get fight boundaries, then use this for detailed analysis.

    Args:
        match_id: The Dota 2 match ID
        start_time: Fight start time in seconds
        end_time: Fight end time in seconds
        interval_seconds: Sampling interval (default 0.5s for 2 samples/second)

    Returns:
        Dictionary with fight replay data including hero states over time
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        fight_replay = _seek_service.get_fight_replay(
            replay_path=data.replay_path,
            start_time=start_time,
            end_time=end_time,
            interval_seconds=interval_seconds,
        )

        return {
            "success": True,
            "match_id": match_id,
            "start_tick": fight_replay.start_tick,
            "end_tick": fight_replay.end_tick,
            "start_time": fight_replay.start_time,
            "start_time_str": fight_replay.start_time_str,
            "end_time": fight_replay.end_time,
            "end_time_str": fight_replay.end_time_str,
            "interval_seconds": interval_seconds,
            "total_snapshots": len(fight_replay.snapshots),
            "snapshots": [
                {
                    "tick": s.tick,
                    "game_time": round(s.game_time, 1),
                    "game_time_str": s.game_time_str,
                    "heroes": [
                        {
                            "hero": h.hero,
                            "team": h.team,
                            "x": round(h.x, 1),
                            "y": round(h.y, 1),
                            "health": h.health,
                            "max_health": h.max_health,
                            "alive": h.alive,
                        }
                        for h in s.heroes
                    ],
                }
                for s in fight_replay.snapshots
            ],
        }

    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": f"Failed to get fight replay: {e}",
        }


def main():
    """Main entry point for the server."""
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print("Dota 2 Match MCP Server v1.0.0")
        return

    print("Dota 2 Match MCP Server starting...", file=sys.stderr)
    print("Resources:", file=sys.stderr)
    print("   dota2://heroes/all", file=sys.stderr)
    print("   dota2://map", file=sys.stderr)
    print("   dota2://pro/players", file=sys.stderr)
    print("   dota2://pro/teams", file=sys.stderr)
    print("Tools:", file=sys.stderr)
    print("   download_replay", file=sys.stderr)
    print("   get_match_info", file=sys.stderr)
    print("   get_match_heroes", file=sys.stderr)
    print("   get_match_players", file=sys.stderr)
    print("   get_match_draft", file=sys.stderr)
    print("   get_match_timeline", file=sys.stderr)
    print("   get_stats_at_minute", file=sys.stderr)
    print("   get_hero_deaths", file=sys.stderr)
    print("   get_combat_log", file=sys.stderr)
    print("   get_fight_combat_log", file=sys.stderr)
    print("   get_item_purchases", file=sys.stderr)
    print("   get_courier_kills", file=sys.stderr)
    print("   get_objective_kills", file=sys.stderr)
    print("   get_rune_pickups", file=sys.stderr)
    print("   search_pro_player", file=sys.stderr)
    print("   search_team", file=sys.stderr)
    print("   get_pro_player", file=sys.stderr)
    print("   get_pro_player_by_name", file=sys.stderr)
    print("   get_team", file=sys.stderr)
    print("   get_team_by_name", file=sys.stderr)
    print("   get_team_matches", file=sys.stderr)
    print("   get_leagues", file=sys.stderr)
    print("   get_pro_matches", file=sys.stderr)
    print("   get_league_matches", file=sys.stderr)
    print("   list_fights (v2)", file=sys.stderr)
    print("   get_teamfights (v2)", file=sys.stderr)
    print("   get_fight (v2)", file=sys.stderr)
    print("   get_camp_stacks (v2)", file=sys.stderr)
    print("   get_jungle_summary (v2)", file=sys.stderr)
    print("   get_lane_summary (v2)", file=sys.stderr)
    print("   get_cs_at_minute (v2)", file=sys.stderr)
    print("   get_hero_positions (v2)", file=sys.stderr)
    print("   get_snapshot_at_time (v2)", file=sys.stderr)
    print("   get_position_timeline (v2)", file=sys.stderr)
    print("   get_fight_replay (v2)", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
