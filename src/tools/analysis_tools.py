"""Analysis MCP tools: jungle, lane, farming patterns, rotations, positions."""

from typing import List, Optional

from fastmcp import Context

from ..models.tool_responses import (
    CampStack,
    CampStacksResponse,
    CSAtMinuteResponse,
    HeroCSData,
    HeroLaneStats,
    HeroPositionTimeline,
    JungleSummaryResponse,
    LaneSummaryResponse,
    LaneWinners,
    PositionPoint,
    PositionTimelineResponse,
    TeamScores,
)
from ..services.models.farming_data import FarmingPatternResponse, ItemTiming
from ..services.models.rotation_data import RotationAnalysisResponse


def register_analysis_tools(mcp, services):
    """Register analysis tools with the MCP server."""
    replay_service = services["replay_service"]
    jungle_service = services["jungle_service"]
    lane_service = services["lane_service"]
    seek_service = services["seek_service"]
    farming_service = services["farming_service"]
    rotation_service = services["rotation_service"]
    heroes_resource = services["heroes_resource"]
    constants_fetcher = services["constants_fetcher"]
    match_fetcher = services["match_fetcher"]

    @mcp.tool
    async def get_camp_stacks(
        match_id: int,
        hero_filter: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> CampStacksResponse:
        """Get all neutral camp stacks in a Dota 2 match."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            stacks = jungle_service.get_camp_stacks(data, hero_filter=hero_filter)
            stack_models = [
                CampStack(
                    game_time=s.game_time,
                    game_time_str=s.game_time_str,
                    stacker=s.stacker,
                    camp_type=s.camp_type,
                    stack_count=s.stack_count,
                )
                for s in stacks
            ]
            return CampStacksResponse(
                success=True,
                match_id=match_id,
                hero_filter=hero_filter,
                total_stacks=len(stacks),
                stacks=stack_models,
            )
        except ValueError as e:
            return CampStacksResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return CampStacksResponse(
                success=False, match_id=match_id, error=f"Failed to get camp stacks: {e}"
            )

    @mcp.tool
    async def get_jungle_summary(
        match_id: int, ctx: Optional[Context] = None
    ) -> JungleSummaryResponse:
        """Get jungle activity summary for a Dota 2 match."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            summary = jungle_service.get_jungle_summary(data)
            efficiency = jungle_service.get_stack_efficiency(data)
            return JungleSummaryResponse(
                success=True,
                match_id=match_id,
                total_stacks=summary.total_stacks,
                stacks_by_hero=summary.stacks_by_hero,
                stack_efficiency_per_10min=efficiency,
            )
        except ValueError as e:
            return JungleSummaryResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return JungleSummaryResponse(
                success=False, match_id=match_id, error=f"Failed to get jungle summary: {e}"
            )

    @mcp.tool
    async def get_lane_summary(
        match_id: int, ctx: Optional[Context] = None
    ) -> LaneSummaryResponse:
        """Get laning phase summary for a Dota 2 match."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            summary = lane_service.get_lane_summary(data)

            opendota_players = await match_fetcher.get_players(match_id)
            opendota_lanes = {}
            for p in opendota_players:
                hero_id = p.get("hero_id")
                if hero_id:
                    hero_name = constants_fetcher.get_hero_name(hero_id)
                    if hero_name:
                        opendota_lanes[hero_name.lower()] = {
                            "lane_name": p.get("lane_name"),
                            "role": p.get("role"),
                        }

            hero_stats = []
            for s in summary.hero_stats:
                od_data = opendota_lanes.get(s.hero.lower(), {})
                hero_stats.append(
                    HeroLaneStats(
                        hero=s.hero,
                        lane=od_data.get("lane_name") or s.lane,
                        role=od_data.get("role") or s.role,
                        team=s.team,
                        last_hits_5min=s.last_hits_5min,
                        last_hits_10min=s.last_hits_10min,
                        denies_5min=s.denies_5min,
                        denies_10min=s.denies_10min,
                        gold_5min=s.gold_5min,
                        gold_10min=s.gold_10min,
                        level_5min=s.level_5min,
                        level_10min=s.level_10min,
                    )
                )

            return LaneSummaryResponse(
                success=True,
                match_id=match_id,
                lane_winners=LaneWinners(
                    top=summary.top_winner,
                    mid=summary.mid_winner,
                    bot=summary.bot_winner,
                ),
                team_scores=TeamScores(
                    radiant=round(summary.radiant_laning_score, 1),
                    dire=round(summary.dire_laning_score, 1),
                ),
                hero_stats=hero_stats,
            )
        except ValueError as e:
            return LaneSummaryResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return LaneSummaryResponse(
                success=False, match_id=match_id, error=f"Failed to get lane summary: {e}"
            )

    @mcp.tool
    async def get_cs_at_minute(
        match_id: int,
        minute: int,
        ctx: Optional[Context] = None,
    ) -> CSAtMinuteResponse:
        """Get last hits, denies, gold, and level for all heroes at a specific minute."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            cs_data = lane_service.get_cs_at_minute(data, minute)
            heroes = [
                HeroCSData(
                    hero=hero_name,
                    team=stats.get("team", "radiant"),
                    last_hits=stats.get("last_hits", 0),
                    denies=stats.get("denies", 0),
                    gold=stats.get("gold", 0),
                    level=stats.get("level", 0),
                )
                for hero_name, stats in cs_data.items()
            ]
            return CSAtMinuteResponse(
                success=True, match_id=match_id, minute=minute, heroes=heroes
            )
        except ValueError as e:
            return CSAtMinuteResponse(
                success=False, match_id=match_id, minute=minute, error=str(e)
            )
        except Exception as e:
            return CSAtMinuteResponse(
                success=False,
                match_id=match_id,
                minute=minute,
                error=f"Failed to get CS at minute {minute}: {e}",
            )

    @mcp.tool
    async def get_position_timeline(
        match_id: int,
        start_time: float,
        end_time: float,
        hero_filter: Optional[str] = None,
        interval_seconds: float = 1.0,
        ctx: Optional[Context] = None,
    ) -> PositionTimelineResponse:
        """Get hero positions over a time range at regular intervals."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            timelines = seek_service.get_position_timeline(
                replay_path=data.replay_path,
                start_time=start_time,
                end_time=end_time,
                hero_filter=hero_filter,
                interval_seconds=interval_seconds,
            )
            hero_timelines = [
                HeroPositionTimeline(
                    hero=t.hero,
                    team=t.team,
                    positions=[
                        PositionPoint(
                            tick=p[0],
                            game_time=round(p[1], 1),
                            x=round(p[2], 1),
                            y=round(p[3], 1),
                        )
                        for p in t.positions
                    ],
                )
                for t in timelines
            ]
            return PositionTimelineResponse(
                success=True,
                match_id=match_id,
                start_time=start_time,
                end_time=end_time,
                interval_seconds=interval_seconds,
                hero_filter=hero_filter,
                heroes=hero_timelines,
            )
        except ValueError as e:
            return PositionTimelineResponse(success=False, match_id=match_id, error=str(e))
        except Exception as e:
            return PositionTimelineResponse(
                success=False, match_id=match_id, error=f"Failed to get position timeline: {e}"
            )

    @mcp.tool
    async def get_farming_pattern(
        match_id: int,
        hero: str,
        start_minute: int = 0,
        end_minute: int = 10,
        ctx: Optional[Context] = None,
    ) -> FarmingPatternResponse:
        """Analyze a hero's farming pattern with camp sequences, power spikes, and routes."""
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        def format_time(seconds: float) -> str:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            match_heroes = await heroes_resource.get_match_heroes(match_id)
            hero_lower = hero.lower()
            hero_id = None

            for h in match_heroes:
                hero_name = h.get("hero_name", "").lower()
                localized_name = h.get("localized_name", "").lower()
                if hero_lower in hero_name or hero_lower in localized_name:
                    hero_id = h.get("hero_id")
                    break

            item_timings_list: List[ItemTiming] = []
            if hero_id:
                raw_items = await match_fetcher.get_player_item_timings(match_id, hero_id)
                for item in raw_items:
                    item_time = item.get("time", 0)
                    if item_time <= (end_minute + 5) * 60:
                        item_timings_list.append(
                            ItemTiming(
                                item=item.get("item", "unknown"),
                                time=float(item_time),
                                time_str=format_time(item_time),
                            )
                        )

            result = farming_service.get_farming_pattern(
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

    @mcp.tool
    async def get_rotation_analysis(
        match_id: int,
        start_minute: int = 0,
        end_minute: int = 20,
        ctx: Optional[Context] = None,
    ) -> RotationAnalysisResponse:
        """
        Analyze hero rotations - movement patterns between lanes and outcomes.

        **NOT FOR HERO PERFORMANCE QUESTIONS** → Use get_hero_performance instead.
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            result = rotation_service.get_rotation_analysis(
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
