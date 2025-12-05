"""
Data models for dense seek analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GameSnapshot:
    """Complete game state at a specific tick."""

    tick: int
    game_time: float
    game_time_str: str

    # Hero states
    heroes: List["HeroSnapshot"] = field(default_factory=list)

    # Team gold totals
    radiant_gold: int = 0
    dire_gold: int = 0

    # Team XP totals
    radiant_xp: int = 0
    dire_xp: int = 0


@dataclass
class HeroSnapshot:
    """Hero state at a specific tick."""

    hero: str
    team: str  # radiant/dire
    player_id: int

    # Position
    x: float
    y: float

    # Stats
    health: int = 0
    max_health: int = 0
    mana: int = 0
    max_mana: int = 0
    level: int = 1

    # Economy
    gold: int = 0
    last_hits: int = 0
    denies: int = 0

    # State
    alive: bool = True


@dataclass
class PositionTimeline:
    """Hero positions over a time range at high resolution."""

    hero: str
    team: str

    # List of (tick, game_time, x, y) tuples
    positions: List[tuple] = field(default_factory=list)


@dataclass
class FightReplay:
    """High-resolution data for a fight."""

    start_tick: int
    end_tick: int
    start_time: float
    end_time: float
    start_time_str: str
    end_time_str: str

    # Snapshots every N ticks during the fight
    snapshots: List[GameSnapshot] = field(default_factory=list)

    # Deaths that occurred during the fight
    deaths: List[Dict] = field(default_factory=list)
