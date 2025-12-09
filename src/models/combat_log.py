"""Pydantic models for combat log data."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DetailLevel(str, Enum):
    """Detail level for combat log queries.

    Controls the verbosity and token usage of combat log responses.
    Use the most restrictive level that meets your analysis needs.
    """

    NARRATIVE = "narrative"
    """Story-telling events only: hero deaths, abilities, purchases, buybacks.
    ~500-2,000 tokens per fight. Best for: "What happened in this fight?"
    """

    TACTICAL = "tactical"
    """Adds hero-to-hero combat detail: damage dealt, debuffs applied.
    ~2,000-5,000 tokens per fight. Best for: "How much damage did X do?"
    """

    FULL = "full"
    """All events including creeps, heals, modifier removes.
    ~50,000+ tokens per fight. WARNING: Can overflow context.
    Best for: Debugging or very specific queries.
    """


class CombatLogEvent(BaseModel):
    """A single combat log event."""

    type: str = Field(description="Event type: DAMAGE, ABILITY, MODIFIER_ADD, DEATH, etc.")
    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    attacker: str = Field(description="Source of the event (hero name without npc_dota_hero_ prefix)")
    attacker_is_hero: bool = Field(description="Whether the attacker is a hero")
    target: str = Field(description="Target of the event")
    target_is_hero: bool = Field(description="Whether the target is a hero")
    ability: Optional[str] = Field(default=None, description="Ability or item involved")
    value: Optional[int] = Field(default=None, description="Damage amount or other numeric value")
    hit: Optional[bool] = Field(
        default=None,
        description="For ABILITY events: whether the ability hit an enemy hero.",
    )
    tick: Optional[int] = Field(default=None, exclude=True, description="Internal replay tick")


class MapLocation(BaseModel):
    """A classified map position."""

    x: float = Field(description="World X coordinate")
    y: float = Field(description="World Y coordinate")
    region: str = Field(description="Map region (e.g., 'radiant_jungle', 'dire_safelane', 'river')")
    lane: Optional[str] = Field(default=None, description="Lane if applicable (top/mid/bot)")
    location: str = Field(description="Human-readable location description")


class HeroDeath(BaseModel):
    """A hero death event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    killer: str = Field(description="Hero or unit that got the kill")
    victim: str = Field(description="Hero that died")
    killer_is_hero: bool = Field(description="Whether the killer was a hero")
    ability: Optional[str] = Field(default=None, description="Ability or item that dealt the killing blow")
    position_x: Optional[float] = Field(default=None, description="World X coordinate of death")
    position_y: Optional[float] = Field(default=None, description="World Y coordinate of death")
    location_description: Optional[str] = Field(default=None, description="Map region description")
    tick: Optional[int] = Field(default=None, exclude=True, description="Internal replay tick")


class FightResult(BaseModel):
    """Result of fight detection around a reference time."""

    fight_start: float = Field(description="Fight start time in seconds")
    fight_start_str: str = Field(description="Fight start formatted as M:SS")
    fight_end: float = Field(description="Fight end time in seconds")
    fight_end_str: str = Field(description="Fight end formatted as M:SS")
    duration: float = Field(description="Fight duration in seconds")
    participants: List[str] = Field(description="Heroes involved in the fight")
    total_events: int = Field(description="Number of combat events in the fight")
    events: List[CombatLogEvent] = Field(description="Combat events in chronological order")


class HeroDeathsResponse(BaseModel):
    """Response for get_hero_deaths tool."""

    success: bool
    match_id: int
    total_deaths: int = Field(default=0)
    deaths: List[HeroDeath] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class CombatLogFilters(BaseModel):
    """Filters applied to combat log query."""

    start_time: Optional[float] = None
    end_time: Optional[float] = None
    hero_filter: Optional[str] = None


class CombatLogResponse(BaseModel):
    """Response for get_combat_log tool."""

    success: bool
    match_id: int
    total_events: int = Field(default=0)
    filters: CombatLogFilters = Field(default_factory=CombatLogFilters)
    events: List[CombatLogEvent] = Field(default_factory=list)
    truncated: bool = Field(
        default=False,
        description="True if results were truncated due to max_events limit"
    )
    detail_level: str = Field(
        default="narrative",
        description="Detail level used: narrative, tactical, or full"
    )
    error: Optional[str] = Field(default=None)


class MultiHeroAbility(BaseModel):
    """A big ability that hit multiple heroes."""

    game_time: float = Field(description="Game time when ability was cast")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    ability: str = Field(description="Internal ability name")
    ability_display: str = Field(description="Human-readable ability name (e.g., 'Chronosphere')")
    caster: str = Field(description="Hero who cast the ability")
    targets: List[str] = Field(default_factory=list, description="Heroes hit by the ability")
    hero_count: int = Field(description="Number of heroes hit")


class KillStreak(BaseModel):
    """A kill streak (double kill, rampage, etc.)."""

    game_time: float = Field(description="Game time of final kill in streak")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    hero: str = Field(description="Hero who achieved the streak")
    streak_type: str = Field(description="Type: double_kill, triple_kill, ultra_kill, rampage")
    kills: int = Field(description="Number of kills in the streak")
    victims: List[str] = Field(default_factory=list, description="Heroes killed in the streak")


class TeamWipe(BaseModel):
    """An ace / team wipe."""

    game_time: float = Field(description="Game time when wipe was completed")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    team_wiped: str = Field(description="Team that was wiped (radiant/dire)")
    duration: float = Field(description="Seconds from first to last death")
    killer_team: str = Field(description="Team that achieved the wipe")


class FightHighlights(BaseModel):
    """Key moments extracted from a fight."""

    multi_hero_abilities: List[MultiHeroAbility] = Field(
        default_factory=list,
        description="Big abilities that hit multiple heroes (Chronosphere, Black Hole, etc.)"
    )
    kill_streaks: List[KillStreak] = Field(
        default_factory=list,
        description="Kill streaks achieved during the fight (double kill, rampage, etc.)"
    )
    team_wipes: List[TeamWipe] = Field(
        default_factory=list,
        description="Team wipes (all 5 heroes of one team killed)"
    )


class FightCombatLogResponse(BaseModel):
    """Response for get_fight_combat_log tool."""

    success: bool
    match_id: int
    hero: Optional[str] = Field(default=None, description="Hero used as anchor for fight detection")
    fight_start: float = Field(default=0.0)
    fight_start_str: str = Field(default="0:00")
    fight_end: float = Field(default=0.0)
    fight_end_str: str = Field(default="0:00")
    duration: float = Field(default=0.0)
    participants: List[str] = Field(default_factory=list)
    total_events: int = Field(default=0)
    events: List[CombatLogEvent] = Field(default_factory=list)
    highlights: Optional[FightHighlights] = Field(
        default=None,
        description="Key moments: multi-hero abilities, kill streaks, team wipes"
    )
    error: Optional[str] = Field(default=None)


class ItemPurchase(BaseModel):
    """A single item purchase event."""

    game_time: float = Field(description="Game time in seconds when item was purchased")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    hero: str = Field(description="Hero that purchased the item")
    item: str = Field(description="Item name (e.g., item_bfury, item_power_treads)")
    tick: Optional[int] = Field(default=None, exclude=True, description="Internal replay tick")


class ItemPurchasesResponse(BaseModel):
    """Response for get_item_purchases tool."""

    success: bool
    match_id: int
    hero_filter: Optional[str] = Field(default=None, description="Hero filter applied")
    total_purchases: int = Field(default=0)
    purchases: List[ItemPurchase] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class CourierKill(BaseModel):
    """A courier kill event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    killer: str = Field(description="Hero that killed the courier")
    killer_is_hero: bool = Field(description="Whether the killer was a hero")
    owner: str = Field(description="Hero who owns the courier that was killed")
    team: str = Field(description="Team whose courier was killed (radiant/dire)")
    position: Optional[MapLocation] = Field(default=None, description="Where the courier was killed")
    tick: Optional[int] = Field(default=None, exclude=True, description="Internal replay tick")


class CourierKillsResponse(BaseModel):
    """Response for get_courier_kills tool."""

    success: bool
    match_id: int
    total_kills: int = Field(default=0)
    kills: List[CourierKill] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class RoshanKill(BaseModel):
    """A Roshan kill event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    killer: str = Field(description="Hero that got the last hit on Roshan")
    team: str = Field(description="Team that killed Roshan (radiant/dire)")
    kill_number: int = Field(description="Which Roshan kill this is (1st, 2nd, etc.)")


class TormentorKill(BaseModel):
    """A Tormentor kill event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    killer: str = Field(description="Hero that got the last hit on Tormentor")
    team: str = Field(description="Team that killed Tormentor (radiant/dire)")
    side: str = Field(description="Which Tormentor was killed (radiant/dire side)")


class TowerKill(BaseModel):
    """A tower destruction event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    tower: str = Field(description="Tower name (e.g., 'radiant_t1_mid')")
    team: str = Field(description="Team that lost the tower (radiant/dire)")
    tier: int = Field(description="Tower tier (1, 2, 3, or 4)")
    lane: str = Field(description="Lane (top/mid/bot/base)")
    killer: str = Field(description="Unit/hero that destroyed the tower")
    killer_is_hero: bool = Field(description="Whether the killer was a hero")


class BarracksKill(BaseModel):
    """A barracks destruction event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    barracks: str = Field(description="Barracks name (e.g., 'radiant_melee_mid')")
    team: str = Field(description="Team that lost the barracks (radiant/dire)")
    lane: str = Field(description="Lane (top/mid/bot)")
    type: str = Field(description="Barracks type (melee/ranged)")
    killer: str = Field(description="Unit/hero that destroyed the barracks")
    killer_is_hero: bool = Field(description="Whether the killer was a hero")


class ObjectiveKillsResponse(BaseModel):
    """Response for get_objective_kills tool."""

    success: bool
    match_id: int
    roshan_kills: List[RoshanKill] = Field(default_factory=list)
    tormentor_kills: List[TormentorKill] = Field(default_factory=list)
    tower_kills: List[TowerKill] = Field(default_factory=list)
    barracks_kills: List[BarracksKill] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class DownloadReplayResponse(BaseModel):
    """Response for download_replay tool."""

    success: bool
    match_id: int
    replay_path: Optional[str] = Field(default=None, description="Path to the downloaded replay file")
    file_size_mb: Optional[float] = Field(default=None, description="Size of the replay file in MB")
    already_cached: bool = Field(default=False, description="Whether the replay was already cached")
    error: Optional[str] = Field(default=None)


class RunePickup(BaseModel):
    """A power rune pickup event."""

    game_time: float = Field(description="Game time in seconds")
    game_time_str: str = Field(description="Game time formatted as M:SS")
    hero: str = Field(description="Hero that picked up the rune")
    rune_type: str = Field(
        description="Type of power rune: haste, double_damage, arcane, etc."
    )
    tick: Optional[int] = Field(default=None, exclude=True, description="Internal replay tick")


class RunePickupsResponse(BaseModel):
    """Response for get_rune_pickups tool."""

    success: bool
    match_id: int
    total_pickups: int = Field(default=0)
    pickups: List[RunePickup] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class AbilityUsage(BaseModel):
    """Usage statistics for a single ability."""

    ability: str = Field(description="Internal ability name (e.g., jakiro_ice_path)")
    total_casts: int = Field(description="Total times ability was cast")
    hero_hits: int = Field(
        description="Times it affected an enemy hero (includes stuns/debuffs from ground-targeted abilities)"
    )
    hit_rate: float = Field(description="Percentage of casts that hit heroes (0-100)")


class FightParticipation(BaseModel):
    """A hero's participation in a single fight."""

    fight_id: str = Field(description="Fight identifier")
    fight_start: float = Field(description="Fight start time in seconds")
    fight_start_str: str = Field(description="Fight start formatted as M:SS")
    fight_end: float = Field(description="Fight end time in seconds")
    fight_end_str: str = Field(description="Fight end formatted as M:SS")
    is_teamfight: bool = Field(description="Whether this was a teamfight (3+ deaths)")
    kills: int = Field(description="Heroes killed by this hero in the fight")
    deaths: int = Field(description="Times this hero died in the fight")
    assists: int = Field(description="Kill assists (dealt damage to victim)")
    abilities_used: List[AbilityUsage] = Field(
        default_factory=list,
        description="Abilities used during this fight with hit counts"
    )
    damage_dealt: int = Field(default=0, description="Total damage dealt to enemy heroes")
    damage_received: int = Field(default=0, description="Total damage received from enemy heroes")


class HeroCombatAnalysisResponse(BaseModel):
    """Response for get_hero_combat_analysis tool."""

    success: bool
    match_id: int
    hero: str = Field(description="Hero analyzed")
    total_fights: int = Field(default=0, description="Total fights participated in")
    total_teamfights: int = Field(default=0, description="Teamfights (3+ deaths) participated in")
    total_kills: int = Field(default=0, description="Total kills across all fights")
    total_deaths: int = Field(default=0, description="Total deaths across all fights")
    total_assists: int = Field(default=0, description="Total assists across all fights")
    ability_summary: List[AbilityUsage] = Field(
        default_factory=list,
        description="Overall ability usage across all fights"
    )
    fights: List[FightParticipation] = Field(
        default_factory=list,
        description="Per-fight breakdown of participation"
    )
    error: Optional[str] = Field(default=None)
