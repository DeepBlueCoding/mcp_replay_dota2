"""
Data models for jungle analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CampStack:
    """A neutral camp stack event."""

    game_time: float
    game_time_str: str
    tick: int
    stacker: str  # Hero who stacked
    camp_type: Optional[str] = None  # small/medium/large/ancient
    stack_count: int = 1  # How many times stacked (if detectable)
    position_x: Optional[float] = None
    position_y: Optional[float] = None


@dataclass
class CampPull:
    """A lane creep pull event (detected from creep deaths near camps)."""

    game_time: float
    game_time_str: str
    tick: int
    puller: str  # Hero who pulled
    lane: str  # safelane/offlane
    team: str  # radiant/dire
    camp_type: Optional[str] = None


@dataclass
class NeutralItemDrop:
    """A neutral item drop event."""

    game_time: float
    game_time_str: str
    tick: int
    hero: str
    item: str
    tier: int  # 1-5


@dataclass
class JungleSummary:
    """Summary of jungle activity in a match."""

    total_stacks: int = 0
    stacks_by_hero: dict = field(default_factory=dict)
    stacks_by_team: dict = field(default_factory=dict)
    total_pulls: int = 0
    pulls_by_hero: dict = field(default_factory=dict)
    neutral_items_found: int = 0
    stacks: List[CampStack] = field(default_factory=list)
    pulls: List[CampPull] = field(default_factory=list)
