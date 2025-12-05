"""
Data models for combat analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HeroDeath:
    """A hero death event."""

    game_time: float
    game_time_str: str
    tick: int
    killer: str
    victim: str
    killer_is_hero: bool
    ability: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    location_description: Optional[str] = None


@dataclass
class DamageEvent:
    """A damage event from combat log."""

    game_time: float
    tick: int
    attacker: str
    target: str
    damage: int
    ability: Optional[str] = None
    attacker_is_hero: bool = False
    target_is_hero: bool = False


@dataclass
class Fight:
    """A fight containing one or more hero deaths."""

    fight_id: str
    start_time: float
    start_time_str: str
    end_time: float
    end_time_str: str
    duration: float
    deaths: List[HeroDeath] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    radiant_deaths: int = 0
    dire_deaths: int = 0

    @property
    def total_deaths(self) -> int:
        return len(self.deaths)

    @property
    def is_teamfight(self) -> bool:
        return self.total_deaths >= 3


@dataclass
class FightResult:
    """Result of fight detection analysis."""

    fights: List[Fight] = field(default_factory=list)
    total_deaths: int = 0
    total_fights: int = 0
    teamfights: int = 0

    @property
    def skirmishes(self) -> int:
        return self.total_fights - self.teamfights


@dataclass
class ItemPurchase:
    """An item purchase event."""

    game_time: float
    game_time_str: str
    tick: int
    hero: str
    item: str


@dataclass
class RunePickup:
    """A rune pickup event."""

    game_time: float
    game_time_str: str
    tick: int
    hero: str
    rune_type: str


@dataclass
class ObjectiveKill:
    """An objective kill (Roshan, tower, barracks, etc.)."""

    game_time: float
    game_time_str: str
    tick: int
    objective_type: str
    objective_name: str
    killer: Optional[str] = None
    team: Optional[str] = None
    extra_info: Optional[dict] = None
