#!/usr/bin/env python3
# ruff: noqa: E402
"""
Dota 2 Match MCP Server - Match-focused analysis

Provides MCP tools for analyzing specific Dota 2 matches using replay files.
All tools require a match_id and work with actual match data.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Add project paths for imports
project_root = Path(__file__).parent.parent
mcp_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(mcp_dir))

from fastmcp import Context, FastMCP

# Create the MCP server instance with coaching instructions
COACHING_INSTRUCTIONS = """
You are a Dota 2 coaching assistant analyzing professional and pub match replays.
Your goal is to provide MEANINGFUL ANALYSIS, not just display raw data.

## Analysis Philosophy
- Never dump raw numbers in tables without context
- Every statistic must be linked to an explanation of WHY it matters
- Focus on PATTERNS and TRENDS, not isolated events
- Provide actionable coaching advice the player can apply in future games

## Workflow for Match Analysis
1. Start with get_match_info for game context (duration, winner, skill level)
2. Use get_draft to understand team compositions and expected playstyles
3. Analyze objectives with get_objective_kills to understand game flow
4. Review deaths with get_hero_deaths to identify patterns
5. Use get_timeline for critical game moments and networth swings

## CRITICAL: Dota 2 Game Knowledge

### Laning Phase Roles (0-10 minutes)
Each position has SPECIFIC responsibilities during laning. Do NOT confuse them:

**Position 1 (Carry/Safelane)**: Farm the safelane. Their ONLY job is to get CS and survive.
They do NOT rotate. They do NOT gank. Deaths in safelane are usually support/mid rotations.

**Position 2 (Mid)**: Farm mid, contest runes. CAN rotate after rune spawns (2:00, 4:00, 6:00+).
Mid rotations with haste/DD rune are common gank opportunities.

**Position 3 (Offlane)**: Pressure enemy carry, get levels, survive. They do NOT rotate early.
Offlaners dying is NORMAL - they're supposed to create space by drawing attention.
An offlaner dying does NOT mean the team "spent resources" - it's the lane matchup.

**Position 4 (Soft Support)**: Pull camps, rotate to gank mid or offlane, secure runes.
These are the PRIMARY early-game rotators via smoke or twin gate portals.

**Position 5 (Hard Support)**: Protect carry in lane, stack camps, place wards.
Can rotate but usually stays to protect carry until 5-7 minutes.

### Common Analysis Mistakes to AVOID
- "Team X killed the offlaner instead of ganking the carry" - WRONG. These are independent events.
  The offlane 2v1 or 3v1 happens regardless of whether supports rotate elsewhere.
- "Carry was farming uncontested because offlaner died" - WRONG. Offlaner deaths don't prevent
  support rotations. The pos 4/5 decide where to rotate, not based on offlane kills.
- "Offlaner should have rotated at 8 minutes" - WRONG. Offlaners need farm and levels.
  Rotations before 10-12 min are for supports and mid only.
- Attributing good carry farm to enemy "not rotating" - Check if enemy supports DID rotate.
  Good carry farm usually means good lane control, not enemy mistakes.

### What Actually Creates Space
- Support rotations to gank mid (forces defensive TP)
- Smoke ganks on enemy jungle
- Offlaner pressuring tower (forces carry to defend or lose tower)
- Taking objectives that force reactions

## Key Analysis Areas

### Objectives & Map Control
- First tower: Which team took it? Who rotated (mid with rune, supports via portal)?
- Identify kill sequences around objectives (defenders TPing, smoke ganks)
- Roshan timing and fights around the pit
- High ground siege attempts and outcomes

### Networth & Economy
- Link networth swings to specific teamfights or objectives
- Identify power spikes from key item completions
- Explain WHEN a team gained/lost advantage and WHY

### Death Pattern Recognition
Look for REPETITIVE death patterns:
- Supports dying out of position (warding without vision, solo rotations)
- Deaths to smoke ganks (lack of defensive wards, predictable farming patterns)
- Vision-related deaths (walking into unwarded areas, missing enemy movements)
- High ground siege deaths (bad initiation, getting counter-initiated)
- Same hero dying in similar situations multiple times

### Teamfight Analysis
- Who initiated? Was it a good or bad fight to take?
- Key abilities used/missed
- Positioning issues that led to deaths
- Items that made the difference (BKB timing, save items)

## Response Format
- Lead with 2-3 key insights that answer "what went wrong/right"
- Use game timestamps when discussing events (e.g., "At 15:23...")
- Tables are OK when they support your explanation, not as standalone data
- End with specific, actionable advice

## Example Good Analysis
"The Radiant support died 4 times between 10:00-15:00, all while placing wards alone.
At 11:42, 12:58, and 14:15, they walked into unwarded jungle and died to smoke ganks.
**Coaching point**: Place wards with a core nearby, or use smokes when moving into
dangerous territory. Consider defensive ward spots that can be placed safely."

## Example Bad Analysis (AVOID)
"Here are the deaths:
| Time | Hero | Killer |
| 11:42 | CM | PA |
| 12:58 | CM | PA |
..."
(Raw table without analysis adds no value)

## Parallel Tool Calls for Efficiency
Many analysis tools are independent and can be called in parallel for faster results.

**Parallelizable tools** (same match, different parameters):
- get_cs_at_minute: Call for minutes 5, 10, 15 simultaneously
- get_stats_at_minute: Call for multiple time points at once
- get_hero_positions: Call for multiple minutes in parallel
- get_snapshot_at_time: Call for multiple game times at once

**Example - Laning phase analysis:**
Instead of calling sequentially:
1. get_cs_at_minute(match_id, 5)
2. get_cs_at_minute(match_id, 10)

Call BOTH in the same response for 2x speed:
- get_cs_at_minute(match_id, 5) AND get_cs_at_minute(match_id, 10)

**When to parallelize:**
- Comparing stats at multiple time points
- Tracking progression (CS at 5/10/15 min)
- Analyzing multiple fights in the same match
- Getting snapshots before/after key events
"""

mcp = FastMCP(
    name="Dota 2 Match Analysis Server",
    instructions=COACHING_INSTRUCTIONS,
)

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
from src.services.cache.replay_cache import ReplayCache as ReplayCacheV2
from src.services.replay.replay_service import ReplayService
from src.utils.constants_fetcher import constants_fetcher
from src.utils.match_fetcher import match_fetcher
from src.utils.pro_scene_fetcher import pro_scene_fetcher

# Initialize services
_replay_cache = ReplayCacheV2()
_replay_service = ReplayService(cache=_replay_cache)

# Combat and Fight services
from src.services.combat.combat_service import CombatService
from src.services.combat.fight_service import FightService

_combat_service = CombatService()
_fight_service = FightService(combat_service=_combat_service)

# Jungle and Lane services
from src.services.jungle.jungle_service import JungleService
from src.services.lane.lane_service import LaneService

_jungle_service = JungleService()
_lane_service = LaneService()

# Seek services (tick-level game state)
from src.services.seek.seek_service import SeekService

_seek_service = SeekService()

# Farming pattern analysis
from src.services.farming.farming_service import FarmingService
from src.services.models.farming_data import FarmingPatternResponse

_farming_service = FarmingService()

# Rotation analysis
from src.services.models.rotation_data import RotationAnalysisResponse
from src.services.rotation.rotation_service import RotationService

_rotation_service = RotationService(
    combat_service=_combat_service,
    fight_service=_fight_service,
)


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
    - 50-95%: Parsing replay
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
async def get_match_timeline(
    match_id: int,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
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
    from src.utils.timeline_parser import timeline_parser

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e)
        }

    timeline = timeline_parser.parse_timeline(data)
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
async def get_stats_at_minute(
    match_id: int,
    minute: int,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get player stats at a specific minute in a Dota 2 match.

    Returns per-player stats:
    - net_worth: Net worth at that minute
    - hero_damage: Cumulative hero damage at that minute
    - kills, deaths, assists: KDA at that minute
    - level: Hero level at that minute

    **Parallel-safe**: Call multiple times with different minutes in parallel
    (e.g., minutes 10, 20, 30) to compare stats across game phases.

    Args:
        match_id: The Dota 2 match ID
        minute: Game minute to get stats for (0-based)

    Returns:
        Dictionary with per-player stats at the specified minute
    """
    from src.utils.timeline_parser import timeline_parser

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e)
        }

    timeline = timeline_parser.parse_timeline(data)
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
async def get_hero_deaths(match_id: int, ctx: Optional[Context] = None) -> HeroDeathsResponse:
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
    from src.models.combat_log import HeroDeath as HeroDeathModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        service_deaths = _combat_service.get_hero_deaths(data)

        deaths = [
            HeroDeathModel(
                game_time=d.game_time,
                game_time_str=d.game_time_str,
                killer=d.killer,
                victim=d.victim,
                killer_is_hero=d.killer_is_hero,
                ability=d.ability,
            )
            for d in service_deaths
        ]

        return HeroDeathsResponse(
            success=True,
            match_id=match_id,
            total_deaths=len(deaths),
            deaths=deaths,
        )
    except ValueError as e:
        return HeroDeathsResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_combat_log(
    match_id: int,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    hero_filter: Optional[str] = None,
    significant_only: bool = False,
    ctx: Optional[Context] = None,
) -> CombatLogResponse:
    """
    Get combat log events from a Dota 2 match with optional filters.

    Returns combat events including damage, abilities, modifiers (buffs/debuffs), and deaths.

    Each event contains:
    - type: DAMAGE, MODIFIER_ADD, ABILITY, DEATH, ITEM, PURCHASE, BUYBACK, etc.
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
        significant_only: If True, returns only story-telling events (abilities, deaths, items,
                         purchases, buybacks) - skips damage ticks and modifier spam.
                         RECOMMENDED for rotation/movement analysis over longer time windows.
                         Default: False (returns all events)

    Returns:
        CombatLogResponse with list of combat log events
    """
    from src.models.combat_log import CombatLogEvent as CombatLogEventModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        service_events = _combat_service.get_combat_log(
            data,
            start_time=start_time,
            end_time=end_time,
            hero_filter=hero_filter,
            significant_only=significant_only,
        )

        events = [
            CombatLogEventModel(
                type=e.type,
                game_time=e.game_time,
                game_time_str=e.game_time_str,
                attacker=e.attacker,
                attacker_is_hero=e.attacker_is_hero,
                target=e.target,
                target_is_hero=e.target_is_hero,
                ability=e.ability,
                value=e.value,
                hit=e.hit,
            )
            for e in service_events
        ]

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
    except ValueError as e:
        return CombatLogResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_fight_combat_log(
    match_id: int,
    reference_time: float,
    hero: Optional[str] = None,
    ctx: Optional[Context] = None,
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
    from src.models.combat_log import CombatLogEvent as CombatLogEventModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        result = _fight_service.get_fight_combat_log(data, reference_time, hero)

        if not result:
            return FightCombatLogResponse(
                success=False,
                match_id=match_id,
                error=f"No fight found at time {reference_time}",
            )

        # Convert service CombatLogEvent to API model
        events = [
            CombatLogEventModel(
                type=e.type,
                game_time=e.game_time,
                game_time_str=e.game_time_str,
                attacker=e.attacker,
                attacker_is_hero=e.attacker_is_hero,
                target=e.target,
                target_is_hero=e.target_is_hero,
                ability=e.ability,
                value=e.value,
                hit=e.hit,
            )
            for e in result["events"]
        ]

        return FightCombatLogResponse(
            success=True,
            match_id=match_id,
            hero=hero,
            fight_start=result["fight_start"],
            fight_start_str=result["fight_start_str"],
            fight_end=result["fight_end"],
            fight_end_str=result["fight_end_str"],
            duration=result["duration"],
            participants=result["participants"],
            total_events=len(events),
            events=events,
        )
    except ValueError as e:
        return FightCombatLogResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_item_purchases(
    match_id: int,
    hero_filter: Optional[str] = None,
    ctx: Optional[Context] = None,
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
    from src.models.combat_log import ItemPurchase as ItemPurchaseModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        service_purchases = _combat_service.get_item_purchases(data, hero_filter=hero_filter)

        purchases = [
            ItemPurchaseModel(
                game_time=p.game_time,
                game_time_str=p.game_time_str,
                hero=p.hero,
                item=p.item,
            )
            for p in service_purchases
        ]

        return ItemPurchasesResponse(
            success=True,
            match_id=match_id,
            hero_filter=hero_filter,
            total_purchases=len(purchases),
            purchases=purchases,
        )
    except ValueError as e:
        return ItemPurchasesResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_courier_kills(
    match_id: int,
    ctx: Optional[Context] = None,
) -> CourierKillsResponse:
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
    from src.models.combat_log import CourierKill as CourierKillModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        service_kills = _combat_service.get_courier_kills(data)

        kills = [
            CourierKillModel(
                game_time=k.game_time,
                game_time_str=k.game_time_str,
                killer=k.killer,
                killer_is_hero=k.killer_is_hero,
                owner=k.owner,
                team=k.team,
            )
            for k in service_kills
        ]

        return CourierKillsResponse(
            success=True,
            match_id=match_id,
            total_kills=len(kills),
            kills=kills,
        )
    except ValueError as e:
        return CourierKillsResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_objective_kills(
    match_id: int,
    ctx: Optional[Context] = None,
) -> ObjectiveKillsResponse:
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
    from src.models.combat_log import (
        BarracksKill,
        RoshanKill,
        TormentorKill,
        TowerKill,
    )

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    def parse_tower_info(name: str) -> tuple:
        """Parse tower tier and lane from name."""
        name_lower = name.lower()
        tier = 1
        lane = "unknown"
        if "tower1" in name_lower or "t1" in name_lower:
            tier = 1
        elif "tower2" in name_lower or "t2" in name_lower:
            tier = 2
        elif "tower3" in name_lower or "t3" in name_lower:
            tier = 3
        elif "tower4" in name_lower or "t4" in name_lower:
            tier = 4
        if "top" in name_lower:
            lane = "top"
        elif "mid" in name_lower:
            lane = "mid"
        elif "bot" in name_lower:
            lane = "bot"
        elif "tower4" in name_lower or "t4" in name_lower:
            lane = "base"
        return tier, lane

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        # Get objective kills from service
        roshan_objs = _combat_service.get_roshan_kills(data)
        tormentor_objs = _combat_service.get_tormentor_kills(data)
        tower_objs = _combat_service.get_tower_kills(data)
        barracks_objs = _combat_service.get_barracks_kills(data)

        # Convert to API models
        roshan_kills = [
            RoshanKill(
                game_time=r.game_time,
                game_time_str=r.game_time_str,
                killer=r.killer or "unknown",
                team=r.team or "unknown",
                kill_number=r.extra_info.get("kill_number", 0) if r.extra_info else 0,
            )
            for r in roshan_objs
        ]

        tormentor_kills = [
            TormentorKill(
                game_time=t.game_time,
                game_time_str=t.game_time_str,
                killer=t.killer or "unknown",
                team=t.team or "unknown",
                side=t.extra_info.get("side", "unknown") if t.extra_info else "unknown",
            )
            for t in tormentor_objs
        ]

        tower_kills = []
        for t in tower_objs:
            tier, lane = parse_tower_info(t.objective_name)
            tower_team = t.extra_info.get("tower_team", "unknown") if t.extra_info else "unknown"
            tower_kills.append(TowerKill(
                game_time=t.game_time,
                game_time_str=t.game_time_str,
                tower=t.objective_name,
                team=tower_team,
                tier=tier,
                lane=lane,
                killer=t.killer or "unknown",
                killer_is_hero=t.killer is not None,
            ))

        barracks_kills = []
        for b in barracks_objs:
            rax_team = b.extra_info.get("barracks_team", "unknown") if b.extra_info else "unknown"
            rax_type = b.extra_info.get("barracks_type", "unknown") if b.extra_info else "unknown"
            lane = "mid"
            if "top" in b.objective_name.lower():
                lane = "top"
            elif "bot" in b.objective_name.lower():
                lane = "bot"
            barracks_kills.append(BarracksKill(
                game_time=b.game_time,
                game_time_str=b.game_time_str,
                barracks=b.objective_name,
                team=rax_team,
                lane=lane,
                type=rax_type,
                killer=b.killer or "unknown",
                killer_is_hero=b.killer is not None,
            ))

        return ObjectiveKillsResponse(
            success=True,
            match_id=match_id,
            roshan_kills=roshan_kills,
            tormentor_kills=tormentor_kills,
            tower_kills=tower_kills,
            barracks_kills=barracks_kills,
        )
    except ValueError as e:
        return ObjectiveKillsResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_rune_pickups(match_id: int, ctx: Optional[Context] = None) -> RunePickupsResponse:
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
    from src.models.combat_log import RunePickup as RunePickupModel

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
        service_pickups = _combat_service.get_rune_pickups(data)

        pickups = [
            RunePickupModel(
                game_time=p.game_time,
                game_time_str=p.game_time_str,
                hero=p.hero,
                rune_type=p.rune_type,
            )
            for p in service_pickups
        ]

        return RunePickupsResponse(
            success=True,
            match_id=match_id,
            total_pickups=len(pickups),
            pickups=pickups,
        )
    except ValueError as e:
        return RunePickupsResponse(
            success=False,
            match_id=match_id,
            error=str(e),
        )


@mcp.tool
async def get_match_draft(
    match_id: int,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
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
    from src.utils.match_info_parser import match_info_parser

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e)
        }

    draft = match_info_parser.get_draft(data)
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


async def _get_pro_names_from_opendota(match_id: int) -> Dict[int, str]:
    """Fetch pro player names from OpenDota match data and manual overrides.

    Returns mapping of steam_id -> pro_name for players with known pro names.
    """
    pro_names: Dict[int, str] = {}

    # Load manual pro name mappings first (account_id -> pro_name)
    manual_names = pro_scene_fetcher.get_manual_pro_names()

    try:
        match_data = await match_fetcher.get_match(match_id)
        if match_data and "players" in match_data:
            for player in match_data["players"]:
                account_id = player.get("account_id")
                if not account_id:
                    continue

                steam_id = account_id + 76561197960265728

                # Check OpenDota pro name first
                pro_name = player.get("name")
                if pro_name:
                    pro_names[steam_id] = pro_name
                # Fall back to manual mappings
                elif str(account_id) in manual_names:
                    pro_names[steam_id] = manual_names[str(account_id)]
    except Exception as e:
        logger.warning(f"Could not fetch pro names from OpenDota: {e}")
    return pro_names


@mcp.tool
async def get_match_info(
    match_id: int,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
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
    from src.utils.match_info_parser import match_info_parser

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)
    except ValueError as e:
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e)
        }

    match_info = match_info_parser.get_match_info(data)
    if not match_info:
        return {
            "success": False,
            "match_id": match_id,
            "error": "Could not parse match info from replay"
        }

    result = match_info.model_dump()

    # Enrich player names with pro names from OpenDota
    pro_names = await _get_pro_names_from_opendota(match_id)
    if pro_names:
        for player_list in [result["players"], result["radiant_players"], result["dire_players"]]:
            for player in player_list:
                steam_id = player.get("steam_id")
                if steam_id and steam_id in pro_names:
                    player["player_name"] = pro_names[steam_id]

    return {
        "success": True,
        **result
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
async def get_pro_matches(
    limit: int = 100,
    tier: Optional[str] = None,
    team_name: Optional[str] = None,
    league_name: Optional[str] = None,
    days_back: Optional[int] = None,
) -> ProMatchesResponse:
    """
    Get recent professional Dota 2 matches with series grouping.

    **IMPORTANT**: By default returns ALL matches including low-tier leagues.
    Use filters to narrow down to relevant matches:
    - tier="premium" for top-tier tournaments (TI, Majors)
    - tier="professional" for mid-tier pro leagues
    - team_name="OG" to find matches for a specific team
    - league_name="SLAM" to find matches in a specific tournament

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
    - "What pro matches happened recently?" -> get_pro_matches(tier="premium")
    - "Show me the latest Team Spirit games" -> get_pro_matches(team_name="Team Spirit")
    - "What matches are in the SLAM tournament?" -> get_pro_matches(league_name="SLAM")

    Args:
        limit: Maximum matches to return (default: 100)
        tier: Filter by league tier - "premium" (TI, Majors), "professional", or "amateur"
        team_name: Filter by team name (fuzzy match, e.g. "OG", "Spirit", "Navi")
        league_name: Filter by league name (contains match, e.g. "SLAM", "ESL", "DreamLeague")
        days_back: Only return matches from the last N days

    Returns:
        ProMatchesResponse with matches and series
    """
    return await pro_scene_resource.get_pro_matches(
        limit=limit,
        tier=tier,
        team_name=team_name,
        league_name=league_name,
        days_back=days_back,
    )


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


# Fight Analysis Tools
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
    ctx: Optional[Context] = None,
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
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific fight.

    Use list_fights first to get available fight_ids.

    Returns:
    - Fight timing (start, end, duration)
    - All participants
    - All deaths with killer, victim, ability, position
    - Damage breakdown (if available)

    **Parallel-safe**: Call multiple times with different fight_ids in parallel
    to analyze multiple fights from the same match efficiently.

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


# Jungle and Lane Analysis Tools
@mcp.tool
async def get_camp_stacks(
    match_id: int,
    hero_filter: Optional[str] = None,
    ctx: Optional[Context] = None,
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
async def get_jungle_summary(match_id: int, ctx: Optional[Context] = None) -> Dict[str, Any]:
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
async def get_lane_summary(match_id: int, ctx: Optional[Context] = None) -> Dict[str, Any]:
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

        # Fetch OpenDota data for authoritative lane assignments
        opendota_players = await match_fetcher.get_players(match_id)
        opendota_lanes = {}
        for p in opendota_players:
            hero_id = p.get("hero_id")
            if hero_id:
                # Get hero name from hero_id
                hero_name = constants_fetcher.get_hero_name(hero_id)
                if hero_name:
                    opendota_lanes[hero_name.lower()] = {
                        "lane_name": p.get("lane_name"),
                        "role": p.get("role"),
                    }

        hero_stats = []
        for s in summary.hero_stats:
            hero_lower = s.hero.lower()
            # Use OpenDota lane data if available
            od_data = opendota_lanes.get(hero_lower, {})
            lane_name = od_data.get("lane_name") or s.lane
            role = od_data.get("role") or s.role

            hero_stats.append({
                "hero": s.hero,
                "lane": lane_name,
                "role": role,
                "team": s.team,
                "last_hits_5min": s.last_hits_5min,
                "last_hits_10min": s.last_hits_10min,
                "denies_5min": s.denies_5min,
                "denies_10min": s.denies_10min,
                "gold_5min": s.gold_5min,
                "gold_10min": s.gold_10min,
                "level_5min": s.level_5min,
                "level_10min": s.level_10min,
            })

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
            "hero_stats": hero_stats,
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
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get last hits, denies, gold, and level for all heroes at a specific minute.

    Useful for tracking CS progression and comparing farm at key timings.

    **Parallel-safe**: Call multiple times with different minutes in parallel
    (e.g., 5, 10, 15) to track laning progression efficiently.

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
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get hero positions at a specific minute in a Dota 2 match.

    Returns X,Y coordinates for all 10 heroes at the specified game minute.
    Useful for understanding lane assignments and rotations.

    **Parallel-safe**: Call multiple times with different minutes in parallel
    to track rotations and map movements efficiently.

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


# Game State Tools
@mcp.tool
async def get_snapshot_at_time(
    match_id: int,
    game_time: float,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get game state snapshot at a specific game time.

    Returns high-resolution state including all hero positions, health, mana, and levels.
    Uses tick-level seeking for precise snapshots.

    **Parallel-safe**: Call multiple times with different game_time values in parallel
    (e.g., before and after a fight) to compare game states efficiently.

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
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get hero positions over a time range at regular intervals.

    Useful for tracking hero movement patterns, rotations, and positioning.

    **Parallel-safe**: Call multiple times with different time ranges or heroes
    in parallel to analyze movement across different game phases efficiently.

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
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get high-resolution replay data for a fight.

    Samples game state at regular intervals during the fight to show
    how hero positions, health, and mana changed throughout.

    Use get_fight to get fight boundaries, then use this for detailed analysis.

    **Parallel-safe**: Call multiple times with different time ranges in parallel
    to analyze multiple fights from the same match efficiently.

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


# Farming Pattern Analysis Tools
@mcp.tool
async def get_farming_pattern(
    match_id: int,
    hero: str,
    start_minute: int = 0,
    end_minute: int = 10,
    ctx: Optional[Context] = None,
) -> FarmingPatternResponse:
    """
    Analyze a hero's farming pattern with camp sequences, power spikes, and routes.

    This is THE tool for questions about "farming pattern", "how did X farm",
    "when did they start jungling", "which camps did they clear", or
    "show me the farming movement minute by minute".

    Returns minute-by-minute breakdown including:
    - camp_sequence: Ordered list of camps cleared each minute (shows farming route)
    - position_at_start/end: Where hero was at start and end of each minute
    - level_timings: When hero reached each level (for power spike analysis)
    - item_timings: When items were purchased (for power spike analysis)
    - Key transitions: first jungle rotation, first large camp, when they left lane

    Each minute shows the actual farming ROUTE:
    - "Min 14: started dire_jungle → large_troll (14:05) → medium_satyr (14:18) →
      ancient_black_dragon (14:35) → large_centaur (14:52)"

    Example questions this tool answers:
    - "What was Terrorblade's farming pattern in the first 10 minutes?"
    - "When did Anti-Mage start jungling?"
    - "Which camps did Luna clear between minutes 5-15?"
    - "How did the carry's farming change after Battle Fury?"

    Args:
        match_id: The Dota 2 match ID
        hero: Hero name to analyze (e.g., "terrorblade", "antimage")
        start_minute: Start of analysis range (default: 0)
        end_minute: End of analysis range (default: 10)

    Returns:
        FarmingPatternResponse with:
        - level_timings: When each level was reached
        - item_timings: When items were purchased
        - minutes: Per-minute data with camp_sequence showing farming route
        - transitions: Key moments (first jungle kill, first large camp)
        - summary: Total lane vs neutral, jungle %, GPM, CS/min
        - creep_kills: All creep kills with timestamps, types, and positions
    """
    from src.services.models.farming_data import ItemTiming

    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    def format_time(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    try:
        # Get replay data
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        # Get match heroes to find hero_id for item timings
        match_heroes = await heroes_resource.get_match_heroes(match_id)
        hero_lower = hero.lower()
        hero_id = None

        # match_heroes is a flat list of all players with hero info
        for h in match_heroes:
            hero_name = h.get("hero_name", "").lower()
            localized_name = h.get("localized_name", "").lower()
            if hero_lower in hero_name or hero_lower in localized_name:
                hero_id = h.get("hero_id")
                break

        # Fetch item timings from OpenDota if we found the hero
        item_timings_list: List[ItemTiming] = []
        if hero_id:
            raw_items = await match_fetcher.get_player_item_timings(match_id, hero_id)
            for item in raw_items:
                item_time = item.get("time", 0)
                # Only include items within our time range (with some buffer)
                if item_time <= (end_minute + 5) * 60:
                    item_timings_list.append(ItemTiming(
                        item=item.get("item", "unknown"),
                        time=float(item_time),
                        time_str=format_time(item_time),
                    ))

        result = _farming_service.get_farming_pattern(
            data=data,
            hero=hero,
            start_minute=start_minute,
            end_minute=end_minute,
            item_timings=item_timings_list,
        )

        return result

    except ValueError as e:
        return FarmingPatternResponse(
            success=False,
            match_id=match_id,
            hero=hero,
            start_minute=start_minute,
            end_minute=end_minute,
            error=str(e),
        )
    except Exception as e:
        return FarmingPatternResponse(
            success=False,
            match_id=match_id,
            hero=hero,
            start_minute=start_minute,
            end_minute=end_minute,
            error=f"Failed to analyze farming pattern: {e}",
        )


# Rotation Analysis Tools
@mcp.tool
async def get_rotation_analysis(
    match_id: int,
    start_minute: int = 0,
    end_minute: int = 20,
    ctx: Optional[Context] = None,
) -> RotationAnalysisResponse:
    """
    Analyze hero rotations - movement patterns between lanes, rune correlations, and outcomes.

    This tool detects when heroes leave their assigned lane and tracks:
    - Where they rotated to and from
    - Whether they picked up a power rune before rotating
    - What happened after the rotation (kill, death, traded, no engagement)
    - Link to fight_id for detailed combat log analysis

    Also tracks rune-related events:
    - Power rune pickups and whether they led to rotations
    - Wisdom rune spawns and whether they were contested (fights nearby)

    Use this to answer questions like:
    - "How many mid rotations happened in the laning phase?"
    - "Did the mid player rotate after picking up runes?"
    - "Which rotations resulted in kills vs deaths?"
    - "Were there any fights at wisdom rune spawns?"
    - "Who was the most active rotator?"

    The outcome field links to fight_id - use get_fight(fight_id) for detailed combat log.

    Args:
        match_id: The Dota 2 match ID
        start_minute: Start of analysis range (default: 0)
        end_minute: End of analysis range (default: 20, covers laning + early mid game)

    Returns:
        RotationAnalysisResponse with:
        - rotations: List of detected rotations with rune/outcome data
        - rune_events: Power rune and wisdom rune events
        - summary: Statistics by hero including success rates
    """
    async def progress_callback(current: int, total: int, message: str) -> None:
        if ctx:
            await ctx.report_progress(current, total)

    try:
        data = await _replay_service.get_parsed_data(match_id, progress=progress_callback)

        result = _rotation_service.get_rotation_analysis(
            data=data,
            start_minute=start_minute,
            end_minute=end_minute,
        )

        return result

    except ValueError as e:
        return RotationAnalysisResponse(
            success=False,
            match_id=match_id,
            start_minute=start_minute,
            end_minute=end_minute,
            error=str(e),
        )
    except Exception as e:
        return RotationAnalysisResponse(
            success=False,
            match_id=match_id,
            start_minute=start_minute,
            end_minute=end_minute,
            error=f"Failed to analyze rotations: {e}",
        )


def main():
    """Main entry point for the server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Dota 2 Match MCP Server")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode: stdio (default) or sse for HTTP/SSE",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8081)),
        help="Port for SSE transport (default: 8081 or PORT env var)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    if args.version:
        print("Dota 2 Match MCP Server v1.0.0")
        return

    print("Dota 2 Match MCP Server starting...", file=sys.stderr)
    print(f"Transport: {args.transport}", file=sys.stderr)
    if args.transport == "sse":
        print(f"Listening on: http://{args.host}:{args.port}", file=sys.stderr)
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
    print("   list_fights", file=sys.stderr)
    print("   get_teamfights", file=sys.stderr)
    print("   get_fight", file=sys.stderr)
    print("   get_camp_stacks", file=sys.stderr)
    print("   get_jungle_summary", file=sys.stderr)
    print("   get_lane_summary", file=sys.stderr)
    print("   get_cs_at_minute", file=sys.stderr)
    print("   get_hero_positions", file=sys.stderr)
    print("   get_snapshot_at_time", file=sys.stderr)
    print("   get_position_timeline", file=sys.stderr)
    print("   get_fight_replay", file=sys.stderr)
    print("   get_farming_pattern", file=sys.stderr)
    print("   get_rotation_analysis", file=sys.stderr)

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
