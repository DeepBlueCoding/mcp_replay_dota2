"""
Data models for lane analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LaneSnapshot:
    """Lane state at a specific time."""

    game_time: float
    game_time_str: str
    tick: int
    lane: str  # top/mid/bot

    # Hero positions in lane
    radiant_heroes: List[str] = field(default_factory=list)
    dire_heroes: List[str] = field(default_factory=list)

    # Lane equilibrium (distance from radiant T1)
    # Positive = towards dire, Negative = towards radiant
    equilibrium_position: Optional[float] = None

    # CS at this point
    radiant_last_hits: int = 0
    dire_last_hits: int = 0
    radiant_denies: int = 0
    dire_denies: int = 0


@dataclass
class HeroLaneStats:
    """Stats for a hero in their lane."""

    hero: str
    lane: str  # safelane/mid/offlane
    role: str  # core/support
    team: str  # radiant/dire

    # CS at different minutes
    last_hits_5min: int = 0
    last_hits_10min: int = 0
    denies_5min: int = 0
    denies_10min: int = 0

    # Gold/XP (if available)
    gold_5min: int = 0
    gold_10min: int = 0
    level_5min: int = 0
    level_10min: int = 0


@dataclass
class LaneSummary:
    """Summary of laning phase for a match."""

    # Per-lane winners (based on CS/gold advantage at 10min)
    top_winner: Optional[str] = None  # radiant/dire
    mid_winner: Optional[str] = None
    bot_winner: Optional[str] = None

    # Overall laning score
    radiant_laning_score: float = 0.0
    dire_laning_score: float = 0.0

    # Per-hero stats
    hero_stats: List[HeroLaneStats] = field(default_factory=list)

    # Timeline of lane states
    lane_timeline: List[LaneSnapshot] = field(default_factory=list)


@dataclass
class HeroPosition:
    """Hero position at a specific time."""

    game_time: float
    tick: int
    hero: str
    x: float
    y: float
    team: str  # radiant/dire
