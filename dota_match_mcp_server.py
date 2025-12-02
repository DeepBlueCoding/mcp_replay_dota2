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
)
from src.resources.heroes_resources import heroes_resource
from src.resources.map_resources import get_cached_map_data
from src.utils.combat_log_parser import combat_log_parser
from src.utils.replay_downloader import ReplayDownloader
from src.utils.timeline_parser import timeline_parser


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
    print("Tools:", file=sys.stderr)
    print("   download_replay", file=sys.stderr)
    print("   get_match_timeline", file=sys.stderr)
    print("   get_stats_at_minute", file=sys.stderr)
    print("   get_hero_deaths", file=sys.stderr)
    print("   get_combat_log", file=sys.stderr)
    print("   get_fight_combat_log", file=sys.stderr)
    print("   get_item_purchases", file=sys.stderr)
    print("   get_courier_kills", file=sys.stderr)
    print("   get_objective_kills", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
