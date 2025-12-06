"""
Data models for rotation analysis.

Tracks hero movements between lanes, correlates with runes and fight outcomes.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RuneCorrelation(BaseModel):
    """Rune pickup correlated with a rotation."""

    rune_type: str = Field(description="Type of rune (haste, dd, invis, etc.)")
    pickup_time: float = Field(description="Game time of pickup in seconds")
    pickup_time_str: str = Field(description="Game time formatted as M:SS")
    seconds_before_rotation: float = Field(
        description="Seconds between rune pickup and rotation start"
    )


class RotationOutcome(BaseModel):
    """Outcome of a rotation - links to fight/kill data."""

    type: str = Field(
        default="no_engagement",
        description="Outcome type: 'kill', 'fight', 'traded', 'no_engagement', 'died'"
    )
    fight_id: Optional[str] = Field(
        default=None,
        description="Fight ID if rotation led to fight (use get_fight for details)"
    )
    deaths_in_window: int = Field(
        default=0, description="Total deaths within 60s of rotation"
    )
    rotation_hero_died: bool = Field(
        default=False, description="Whether the rotating hero died"
    )
    kills_by_rotation_hero: List[str] = Field(
        default_factory=list,
        description="Heroes killed by the rotating hero"
    )


class Rotation(BaseModel):
    """A single rotation event."""

    rotation_id: str = Field(description="Unique rotation identifier")
    hero: str = Field(description="Hero that rotated")
    role: str = Field(description="Inferred role: mid, support, offlane, carry")
    game_time: float = Field(description="Game time rotation started (seconds)")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    from_lane: str = Field(description="Lane rotated from (mid, top, bot, jungle)")
    to_lane: str = Field(description="Lane rotated to")
    rune_before: Optional[RuneCorrelation] = Field(
        default=None,
        description="Rune picked up before rotation (within 60s)"
    )
    outcome: RotationOutcome = Field(
        default_factory=RotationOutcome,
        description="What happened after the rotation"
    )
    travel_time_seconds: float = Field(
        default=0.0, description="Time to travel between lanes"
    )
    returned_to_lane: bool = Field(
        default=False, description="Whether hero returned to original lane"
    )
    return_time: Optional[float] = Field(
        default=None, description="Game time when hero returned (seconds)"
    )
    return_time_str: Optional[str] = Field(
        default=None, description="Return time formatted as M:SS"
    )


class PowerRuneEvent(BaseModel):
    """Power rune spawn and pickup event."""

    spawn_time: float = Field(description="Spawn time in seconds")
    spawn_time_str: str = Field(description="Spawn time formatted as M:SS")
    location: str = Field(description="top or bot river")
    taken_by: Optional[str] = Field(
        default=None, description="Hero who took the rune"
    )
    pickup_time: Optional[float] = Field(
        default=None, description="When it was picked up"
    )
    led_to_rotation: bool = Field(
        default=False, description="Whether taker rotated within 60s"
    )
    rotation_id: Optional[str] = Field(
        default=None, description="Linked rotation ID if applicable"
    )


class WisdomRuneEvent(BaseModel):
    """Wisdom rune spawn event with fight correlation."""

    spawn_time: float = Field(description="Spawn time in seconds (7:00, 14:00, etc.)")
    spawn_time_str: str = Field(description="Spawn time formatted as M:SS")
    location: str = Field(description="radiant_jungle or dire_jungle")
    taken_by: Optional[str] = Field(
        default=None, description="Hero who took the rune"
    )
    contested: bool = Field(
        default=False, description="Whether there was a fight for this rune"
    )
    fight_id: Optional[str] = Field(
        default=None, description="Fight ID if contested (use get_fight for details)"
    )
    deaths_nearby: int = Field(
        default=0, description="Deaths within range of wisdom rune"
    )


class RuneRotations(BaseModel):
    """Rune-centric view of rotations."""

    power_runes: List[PowerRuneEvent] = Field(
        default_factory=list, description="Power rune events (6:00, 8:00, ...)"
    )
    wisdom_runes: List[WisdomRuneEvent] = Field(
        default_factory=list, description="Wisdom rune events (7:00, 14:00, ...)"
    )


class HeroRotationStats(BaseModel):
    """Rotation statistics for a single hero."""

    hero: str
    role: str
    total_rotations: int = 0
    successful_ganks: int = Field(
        default=0, description="Rotations resulting in kill without dying"
    )
    failed_ganks: int = Field(
        default=0, description="Rotations where hero died or no engagement"
    )
    trades: int = Field(
        default=0, description="Rotations resulting in kill but also died"
    )
    rune_rotations: int = Field(
        default=0, description="Rotations with rune pickup before"
    )


class RotationSummary(BaseModel):
    """Summary statistics for all rotations."""

    total_rotations: int = 0
    by_hero: Dict[str, HeroRotationStats] = Field(default_factory=dict)
    runes_leading_to_kills: int = Field(
        default=0, description="Rune pickups followed by kill within 60s"
    )
    wisdom_rune_fights: int = Field(
        default=0, description="Fights at wisdom rune spawns"
    )
    most_active_rotator: Optional[str] = Field(
        default=None, description="Hero with most rotations"
    )


class RotationAnalysisResponse(BaseModel):
    """Response for get_rotation_analysis tool."""

    success: bool
    match_id: int
    start_minute: int = Field(description="Start of analysis range")
    end_minute: int = Field(description="End of analysis range")
    rotations: List[Rotation] = Field(
        default_factory=list, description="All detected rotations"
    )
    rune_events: RuneRotations = Field(
        default_factory=RuneRotations,
        description="Rune-centric view of rotations"
    )
    summary: RotationSummary = Field(
        default_factory=RotationSummary, description="Summary statistics"
    )
    error: Optional[str] = Field(default=None)
