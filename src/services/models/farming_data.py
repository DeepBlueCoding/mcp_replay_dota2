"""
Data models for farming pattern analysis.

Provides minute-by-minute breakdown of creep kills, positions, and farm efficiency.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CreepKill(BaseModel):
    """A single creep kill event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    creep_name: str = Field(description="Full creep name")
    creep_type: str = Field(description="Creep type: lane, neutral, or other")
    neutral_camp: Optional[str] = Field(
        default=None,
        description="Neutral camp type if applicable (e.g., 'satyr', 'centaur')"
    )


class MinuteFarmingData(BaseModel):
    """Farming data for a single minute."""

    minute: int = Field(description="Game minute")
    lane_creeps_killed: int = Field(
        default=0, description="Lane creeps killed during this minute"
    )
    neutral_creeps_killed: int = Field(
        default=0, description="Neutral creeps killed during this minute"
    )
    neutral_camps_detail: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of neutral kills by camp type (e.g., {'satyr': 3, 'centaur': 2})"
    )
    position_x: Optional[float] = Field(
        default=None, description="Hero X position at minute mark"
    )
    position_y: Optional[float] = Field(
        default=None, description="Hero Y position at minute mark"
    )
    map_area: Optional[str] = Field(
        default=None, description="Map area at minute mark (e.g., 'dire_safelane', 'radiant_jungle')"
    )
    gold: int = Field(default=0, description="Net worth at minute mark")
    last_hits: int = Field(default=0, description="Total last hits at minute mark")
    denies: int = Field(default=0, description="Total denies at minute mark")
    level: int = Field(default=1, description="Hero level at minute mark")


class FarmingTransitions(BaseModel):
    """Key transition points in farming pattern."""

    first_jungle_kill_time: Optional[float] = Field(
        default=None, description="Game time of first neutral creep kill (seconds)"
    )
    first_jungle_kill_str: Optional[str] = Field(
        default=None, description="Game time of first neutral creep kill (M:SS)"
    )
    first_large_camp_time: Optional[float] = Field(
        default=None, description="Game time of first large/ancient camp kill"
    )
    first_large_camp_str: Optional[str] = Field(
        default=None, description="Game time of first large camp kill (M:SS)"
    )
    left_lane_time: Optional[float] = Field(
        default=None, description="Game time when hero first moved to jungle for extended farm"
    )
    left_lane_str: Optional[str] = Field(
        default=None, description="Game time when left lane (M:SS)"
    )


class FarmingSummary(BaseModel):
    """Summary statistics for farming pattern."""

    total_lane_creeps: int = Field(
        default=0, description="Total lane creeps killed in the time range"
    )
    total_neutral_creeps: int = Field(
        default=0, description="Total neutral creeps killed in the time range"
    )
    jungle_percentage: float = Field(
        default=0.0, description="Percentage of farm from jungle (0-100)"
    )
    gpm: float = Field(default=0.0, description="Gold per minute in the time range")
    cs_per_min: float = Field(
        default=0.0, description="Creep score per minute in the time range"
    )
    camps_cleared: Dict[str, int] = Field(
        default_factory=dict,
        description="Total neutral kills by camp type"
    )


class FarmingPatternResponse(BaseModel):
    """Response for get_farming_pattern tool."""

    success: bool
    match_id: int
    hero: str = Field(description="Hero name analyzed")
    start_minute: int = Field(description="Start of analysis range")
    end_minute: int = Field(description="End of analysis range")
    minutes: List[MinuteFarmingData] = Field(
        default_factory=list,
        description="Minute-by-minute farming breakdown"
    )
    transitions: FarmingTransitions = Field(
        default_factory=FarmingTransitions,
        description="Key transition points in farming pattern"
    )
    summary: FarmingSummary = Field(
        default_factory=FarmingSummary,
        description="Summary statistics"
    )
    creep_kills: List[CreepKill] = Field(
        default_factory=list,
        description="All creep kills in chronological order"
    )
    error: Optional[str] = Field(default=None)
