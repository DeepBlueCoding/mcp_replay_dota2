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

from fastmcp import FastMCP

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
    "dota2://match/{match_id}/heroes",
    name="Match Heroes",
    description="The 10 heroes in a match: hero info, lane, role, KDA, items, GPM/XPM, player info",
    mime_type="application/json"
)
async def match_heroes_resource(match_id: str) -> Dict[str, Any]:
    """
    MCP resource providing complete hero data for a match.

    Returns per-hero:
    - Hero: hero_id, hero_name, localized_name, primary_attr, attack_type, roles
    - Performance: kills, deaths, assists, last_hits, GPM, XPM, net_worth, hero_damage
    - Position: team (radiant/dire), lane, role (core/support)
    - Items: item_0 through item_5, item_neutral
    - Player: player_name, pro_name (who is controlling this hero)

    Args:
        match_id: The Dota 2 match ID as a string

    Returns:
        Dictionary with radiant and dire team heroes
    """
    try:
        match_id_int = int(match_id)
        heroes = await heroes_resource.get_match_heroes(match_id_int)
        if heroes:
            radiant = [h for h in heroes if h.get("team") == "radiant"]
            dire = [h for h in heroes if h.get("team") == "dire"]
            return {
                "match_id": match_id_int,
                "radiant": radiant,
                "dire": dire,
            }
        return {"error": f"Could not fetch heroes for match {match_id}"}
    except ValueError:
        return {"error": f"Invalid match ID: {match_id}"}


@mcp.resource(
    "dota2://match/{match_id}/players",
    name="Match Players",
    description="The 10 players in a match with their player info and which hero they played",
    mime_type="application/json"
)
async def match_players_resource(match_id: str) -> Dict[str, Any]:
    """
    MCP resource providing player-to-hero mapping for a match.

    Returns per-player:
    - Player: player_name (Steam name), pro_name (professional name if known), account_id
    - Team: radiant or dire
    - Hero: hero_id, hero_name, localized_name

    Args:
        match_id: The Dota 2 match ID as a string

    Returns:
        Dictionary with radiant and dire team players
    """
    try:
        match_id_int = int(match_id)
        heroes = await heroes_resource.get_match_heroes(match_id_int)
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
                "match_id": match_id_int,
                "radiant": radiant,
                "dire": dire,
            }
        return {"error": f"Could not fetch players for match {match_id}"}
    except ValueError:
        return {"error": f"Invalid match ID: {match_id}"}


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


@mcp.resource(
    "dota2://pro/player/{account_id}",
    name="Pro Player Details",
    description="Detailed info for a specific pro player by account ID",
    mime_type="application/json"
)
async def pro_player_resource(account_id: str) -> Dict[str, Any]:
    """
    MCP resource providing details for a specific pro player.

    Args:
        account_id: Player's Steam account ID as string

    Returns:
        Player details including team info and aliases
    """
    try:
        account_id_int = int(account_id)
        response = await pro_scene_resource.get_player(account_id_int)
        return response.model_dump()
    except ValueError:
        return {"success": False, "error": f"Invalid account ID: {account_id}"}


@mcp.resource(
    "dota2://pro/team/{team_id}",
    name="Pro Team Details",
    description="Detailed info for a specific team including current roster",
    mime_type="application/json"
)
async def pro_team_resource(team_id: str) -> Dict[str, Any]:
    """
    MCP resource providing details for a specific team.

    Args:
        team_id: Team ID as string

    Returns:
        Team details including roster and aliases
    """
    try:
        team_id_int = int(team_id)
        response = await pro_scene_resource.get_team(team_id_int)
        return response.model_dump()
    except ValueError:
        return {"success": False, "error": f"Invalid team ID: {team_id}"}


# Define MCP Tools
@mcp.tool
async def download_replay(match_id: int) -> DownloadReplayResponse:
    """
    Download and cache the replay file for a Dota 2 match.

    Use this tool FIRST before asking analysis questions about a match.
    Replay files are large (50-400MB) and can take 1-5 minutes to download.

    Once downloaded, the replay is cached locally and subsequent queries
    for the same match will be instant.

    Args:
        match_id: The Dota 2 match ID (from OpenDota, Dotabuff, or in-game)

    Returns:
        DownloadReplayResponse with success status and file info
    """
    downloader = ReplayDownloader()

    # Check if already cached
    existing_path = downloader.get_replay_path(match_id)
    if existing_path:
        file_size_mb = existing_path.stat().st_size / (1024 * 1024)
        return DownloadReplayResponse(
            success=True,
            match_id=match_id,
            replay_path=str(existing_path),
            file_size_mb=round(file_size_mb, 1),
            already_cached=True,
        )

    # Download the replay
    replay_path = await downloader.download_replay(match_id)

    if not replay_path:
        return DownloadReplayResponse(
            success=False,
            match_id=match_id,
            error="Could not download replay. The match may be too old, private, or the replay is not available on OpenDota."
        )

    file_size_mb = replay_path.stat().st_size / (1024 * 1024)
    return DownloadReplayResponse(
        success=True,
        match_id=match_id,
        replay_path=str(replay_path),
        file_size_mb=round(file_size_mb, 1),
        already_cached=False,
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


def main():
    """Main entry point for the server."""
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print("Dota 2 Match MCP Server v1.0.0")
        return

    print("Dota 2 Match MCP Server starting...", file=sys.stderr)
    print("Resources:", file=sys.stderr)
    print("   dota2://heroes/all", file=sys.stderr)
    print("   dota2://map", file=sys.stderr)
    print("   dota2://match/{match_id}/heroes", file=sys.stderr)
    print("   dota2://match/{match_id}/players", file=sys.stderr)
    print("   dota2://pro/players", file=sys.stderr)
    print("   dota2://pro/teams", file=sys.stderr)
    print("   dota2://pro/player/{account_id}", file=sys.stderr)
    print("   dota2://pro/team/{team_id}", file=sys.stderr)
    print("Tools:", file=sys.stderr)
    print("   download_replay", file=sys.stderr)
    print("   get_match_info", file=sys.stderr)
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

    mcp.run()


if __name__ == "__main__":
    main()
