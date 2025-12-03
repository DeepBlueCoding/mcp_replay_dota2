"""Pydantic models for Dota 2 map data."""

from typing import List, Optional

from pydantic import BaseModel, Field


class MapCoordinate(BaseModel):
    """A position on the Dota 2 map."""

    x: float = Field(description="World X coordinate")
    y: float = Field(description="World Y coordinate")


class Tower(BaseModel):
    """A tower on the map."""

    name: str = Field(description="Tower identifier (e.g., 'radiant_t1_mid')")
    team: str = Field(description="Team: radiant or dire")
    tier: int = Field(description="Tower tier: 1, 2, 3, or 4")
    lane: str = Field(description="Lane: top, mid, bot, or base")
    position: MapCoordinate


class Barracks(BaseModel):
    """A barracks building."""

    name: str = Field(description="Barracks identifier")
    team: str = Field(description="Team: radiant or dire")
    lane: str = Field(description="Lane: top, mid, or bot")
    type: str = Field(description="Type: melee or ranged")
    position: MapCoordinate


class Ancient(BaseModel):
    """The Ancient (main objective)."""

    team: str = Field(description="Team: radiant or dire")
    position: MapCoordinate


class NeutralCamp(BaseModel):
    """A neutral creep camp."""

    name: str = Field(description="Camp identifier")
    side: str = Field(description="Map side: radiant or dire")
    tier: str = Field(description="Camp tier: small, medium, large, or ancient")
    position: MapCoordinate


class RuneSpawn(BaseModel):
    """A rune spawn location."""

    name: str = Field(description="Rune spawn identifier")
    type: str = Field(description="Rune type: bounty, power, wisdom, or water")
    position: MapCoordinate


class RuneTypeInfo(BaseModel):
    """Information about a specific rune type."""

    name: str = Field(description="Rune type name")
    first_spawn: int = Field(description="First spawn time in seconds (game time)")
    interval: int = Field(description="Spawn interval in seconds (0 if single spawn)")
    effect: str = Field(description="What this rune does when picked up")
    duration: Optional[int] = Field(default=None, description="Buff duration in seconds (if applicable)")


class RuneRules(BaseModel):
    """Spawn rules and information for all rune types."""

    power_runes: RuneTypeInfo = Field(description="Power runes (river): haste, DD, arcane, invis, regen, shield")
    bounty_runes: RuneTypeInfo = Field(description="Bounty runes (jungle): grants gold to team")
    wisdom_runes: RuneTypeInfo = Field(description="Wisdom runes (near bases): grants XP")
    water_runes: RuneTypeInfo = Field(description="Water runes (river): restores HP/mana, early game only")
    power_rune_types: List[str] = Field(description="All possible power rune variants")


class Outpost(BaseModel):
    """An outpost location."""

    name: str = Field(description="Outpost identifier")
    side: str = Field(description="Map side: radiant or dire")
    position: MapCoordinate


class Shop(BaseModel):
    """A shop location."""

    name: str = Field(description="Shop identifier")
    type: str = Field(description="Shop type: base, secret, or side")
    team: Optional[str] = Field(default=None, description="Team if team-specific")
    position: MapCoordinate


class Landmark(BaseModel):
    """A notable map landmark."""

    name: str = Field(description="Landmark name")
    description: str = Field(description="What this landmark is")
    position: MapCoordinate


class MapLane(BaseModel):
    """A lane path."""

    name: str = Field(description="Lane name: top, mid, or bot")
    radiant_name: str = Field(description="Radiant perspective name (e.g., 'offlane')")
    dire_name: str = Field(description="Dire perspective name (e.g., 'safelane')")


class MapData(BaseModel):
    """Complete Dota 2 map data."""

    map_bounds: dict = Field(description="Map coordinate bounds")
    towers: List[Tower] = Field(description="All towers")
    barracks: List[Barracks] = Field(description="All barracks")
    ancients: List[Ancient] = Field(description="Both team ancients")
    neutral_camps: List[NeutralCamp] = Field(description="All neutral camps")
    rune_spawns: List[RuneSpawn] = Field(description="All rune spawn locations")
    rune_rules: RuneRules = Field(description="Rune spawn timing rules and effects")
    outposts: List[Outpost] = Field(description="Both outposts")
    shops: List[Shop] = Field(description="All shops")
    landmarks: List[Landmark] = Field(description="Notable landmarks")
    lanes: List[MapLane] = Field(description="Lane information")
