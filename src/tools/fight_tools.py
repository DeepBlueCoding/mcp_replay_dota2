"""Fight-related MCP tools: fight detection, teamfights, fight replay."""

from typing import Literal, Optional

from fastmcp import Context

from ..models.combat_log import (
    CombatLogEvent as CombatLogEventModel,
)
from ..models.combat_log import (
    DetailLevel,
    FightCombatLogResponse,
)
from ..models.combat_log import (
    FightHighlights as FightHighlightsModel,
)
from ..models.combat_log import (
    KillStreak as KillStreakModel,
)
from ..models.combat_log import (
    MultiHeroAbility as MultiHeroAbilityModel,
)
from ..models.combat_log import (
    TeamWipe as TeamWipeModel,
)
from ..models.tool_responses import (
    FightDeath,
    FightDeathDetail,
    FightDetailResponse,
    FightListResponse,
    FightReplayResponse,
    FightSnapshot,
    FightSnapshotHero,
    FightSummary,
    TeamfightsResponse,
)


def register_fight_tools(mcp, services):
    """Register fight-related tools with the MCP server."""
    replay_service = services["replay_service"]
    fight_service = services["fight_service"]
    seek_service = services["seek_service"]

    @mcp.tool
    async def get_fight_combat_log(
        match_id: int,
        reference_time: float,
        hero: Optional[str] = None,
        detail_level: Literal["narrative", "tactical", "full"] = "narrative",
        max_events: int = 200,
        ctx: Optional[Context] = None,
    ) -> FightCombatLogResponse:
        """
        Get combat log for ONE SPECIFIC FIGHT at a known time.

        **WHEN TO USE THIS TOOL:**
        - You have a specific death time and want details about that fight
        - You're drilling into a specific moment (e.g., "What happened at 25:30?")

        **DO NOT USE THIS TOOL FOR:**
        - "How did X hero perform?" → Use get_hero_performance instead
        - "Show me all teamfights" → Use get_teamfights instead
        - "List all fights" → Use list_fights instead

        Auto-detects fight boundaries around reference_time.

        Detail levels (use "narrative" for most queries):
        - **narrative** (default): Deaths, abilities, purchases
        - **tactical**: Adds damage events (only for debugging)
        - **full**: All events (debugging only)

        Args:
            match_id: The Dota 2 match ID
            reference_time: Game time in seconds (e.g., from get_hero_deaths)
            hero: Optional hero to anchor detection
            detail_level: Use "narrative" unless debugging
            max_events: Max events (default 200)
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            level = DetailLevel(detail_level)
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            result = fight_service.get_fight_combat_log(
                data, reference_time, hero,
                detail_level=level,
                max_events=max_events,
            )

            if not result:
                return FightCombatLogResponse(
                    success=False,
                    match_id=match_id,
                    error=f"No fight found at time {reference_time}",
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
                for e in result["events"]
            ]

            highlights_data = result.get("highlights")
            highlights = None
            if highlights_data:
                highlights = FightHighlightsModel(
                    multi_hero_abilities=[
                        MultiHeroAbilityModel(
                            game_time=mha.game_time,
                            game_time_str=mha.game_time_str,
                            ability=mha.ability,
                            ability_display=mha.ability_display,
                            caster=mha.caster,
                            targets=mha.targets,
                            hero_count=mha.hero_count,
                        )
                        for mha in highlights_data.multi_hero_abilities
                    ],
                    kill_streaks=[
                        KillStreakModel(
                            game_time=ks.game_time,
                            game_time_str=ks.game_time_str,
                            hero=ks.hero,
                            streak_type=ks.streak_type,
                            kills=ks.kills,
                            victims=ks.victims,
                        )
                        for ks in highlights_data.kill_streaks
                    ],
                    team_wipes=[
                        TeamWipeModel(
                            game_time=tw.game_time,
                            game_time_str=tw.game_time_str,
                            team_wiped=tw.team_wiped,
                            duration=tw.duration,
                            killer_team=tw.killer_team,
                        )
                        for tw in highlights_data.team_wipes
                    ],
                )

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
                highlights=highlights,
            )
        except ValueError as e:
            return FightCombatLogResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def list_fights(match_id: int, ctx: Context) -> FightListResponse:
        """
        List all fights in a Dota 2 match.

        **NOT FOR HERO PERFORMANCE QUESTIONS** → Use get_hero_performance instead.
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            summary = fight_service.get_fight_summary(data)

            fights = [
                FightSummary(
                    fight_id=f.get("fight_id", ""),
                    start_time=f.get("start_time", 0.0),
                    start_time_str=f.get("start_time_str", "0:00"),
                    end_time=f.get("end_time", 0.0),
                    end_time_str=f.get("end_time_str", "0:00"),
                    duration_seconds=f.get("duration_seconds", 0.0),
                    total_deaths=f.get("total_deaths", 0),
                    is_teamfight=f.get("is_teamfight", False),
                    participants=f.get("participants", []),
                    deaths=[
                        FightDeath(
                            game_time=d.get("game_time", 0.0),
                            game_time_str=d.get("game_time_str", "0:00"),
                            killer=d.get("killer", ""),
                            victim=d.get("victim", ""),
                            ability=d.get("ability"),
                        )
                        for d in f.get("deaths", [])
                    ],
                )
                for f in summary.get("fights", [])
            ]

            return FightListResponse(
                success=True,
                match_id=match_id,
                total_fights=summary.get("total_fights", 0),
                teamfights=summary.get("teamfights", 0),
                skirmishes=summary.get("skirmishes", 0),
                total_deaths=summary.get("total_deaths", 0),
                fights=fights,
            )
        except ValueError as e:
            return FightListResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return FightListResponse(success=False, match_id=match_id, error=f"Failed to analyze fights: {e}")

    @mcp.tool
    async def get_teamfights(
        match_id: int,
        min_deaths: int = 3,
        ctx: Optional[Context] = None,
    ) -> TeamfightsResponse:
        """
        Get only teamfights from a Dota 2 match.

        **NOT FOR HERO PERFORMANCE QUESTIONS** → Use get_hero_performance instead.
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            teamfights = fight_service.get_teamfights(data, min_deaths=min_deaths)

            fights = [
                FightSummary(
                    fight_id=f.fight_id,
                    start_time=f.start_time,
                    start_time_str=f.start_time_str,
                    end_time=f.end_time,
                    end_time_str=f.end_time_str,
                    duration_seconds=round(f.duration, 1),
                    total_deaths=f.total_deaths,
                    is_teamfight=True,
                    participants=f.participants,
                    deaths=[
                        FightDeath(
                            game_time=d.game_time,
                            game_time_str=d.game_time_str,
                            killer=d.killer,
                            victim=d.victim,
                            ability=d.ability,
                        )
                        for d in f.deaths
                    ],
                )
                for f in teamfights
            ]

            return TeamfightsResponse(
                success=True,
                match_id=match_id,
                min_deaths_threshold=min_deaths,
                total_teamfights=len(teamfights),
                teamfights=fights,
            )
        except ValueError as e:
            return TeamfightsResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return TeamfightsResponse(success=False, match_id=match_id, error=f"Failed to get teamfights: {e}")

    @mcp.tool
    async def get_fight(
        match_id: int,
        fight_id: str,
        ctx: Optional[Context] = None,
    ) -> FightDetailResponse:
        """Get detailed information about a specific fight."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            fight = fight_service.get_fight_by_id(data, fight_id)

            if not fight:
                return FightDetailResponse(
                    success=False,
                    match_id=match_id,
                    error=f"Fight '{fight_id}' not found. Use list_fights to see available fights.",
                )

            deaths = [
                FightDeathDetail(
                    game_time=d.game_time,
                    game_time_str=d.game_time_str,
                    killer=d.killer,
                    killer_is_hero=d.killer_is_hero,
                    victim=d.victim,
                    ability=d.ability,
                    position_x=d.position_x,
                    position_y=d.position_y,
                )
                for d in fight.deaths
            ]

            return FightDetailResponse(
                success=True,
                match_id=match_id,
                fight_id=fight.fight_id,
                start_time=fight.start_time,
                start_time_str=fight.start_time_str,
                start_time_seconds=fight.start_time,
                end_time=fight.end_time,
                end_time_str=fight.end_time_str,
                end_time_seconds=fight.end_time,
                duration_seconds=round(fight.duration, 1),
                is_teamfight=fight.is_teamfight,
                total_deaths=fight.total_deaths,
                participants=fight.participants,
                deaths=deaths,
            )
        except ValueError as e:
            return FightDetailResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_fight_replay(
        match_id: int,
        start_time: float,
        end_time: float,
        interval_seconds: float = 0.5,
        ctx: Optional[Context] = None,
    ) -> FightReplayResponse:
        """Get high-resolution replay data for a fight."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)

            fight_replay = seek_service.get_fight_replay(
                replay_path=data.replay_path,
                start_time=start_time,
                end_time=end_time,
                interval_seconds=interval_seconds,
            )

            snapshots = [
                FightSnapshot(
                    tick=s.tick,
                    game_time=round(s.game_time, 1),
                    game_time_str=s.game_time_str,
                    heroes=[
                        FightSnapshotHero(
                            hero=h.hero,
                            team=h.team,
                            x=round(h.x, 1),
                            y=round(h.y, 1),
                            health=h.health,
                            max_health=h.max_health,
                            alive=h.alive,
                        )
                        for h in s.heroes
                    ],
                )
                for s in fight_replay.snapshots
            ]

            return FightReplayResponse(
                success=True,
                match_id=match_id,
                start_tick=fight_replay.start_tick,
                end_tick=fight_replay.end_tick,
                start_time=fight_replay.start_time,
                start_time_str=fight_replay.start_time_str,
                end_time=fight_replay.end_time,
                end_time_str=fight_replay.end_time_str,
                interval_seconds=interval_seconds,
                total_snapshots=len(fight_replay.snapshots),
                snapshots=snapshots,
            )
        except ValueError as e:
            return FightReplayResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return FightReplayResponse(success=False, match_id=match_id, error=f"Failed to get fight replay: {e}")
