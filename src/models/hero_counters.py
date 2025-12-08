"""Pydantic models for hero counter pick data."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CounterMatchup(BaseModel):
    """A single counter matchup between two heroes."""

    hero_id: int = Field(description="Counter hero ID")
    hero_name: str = Field(description="Hero internal name (e.g., 'npc_dota_hero_axe')")
    localized_name: str = Field(description="Hero display name (e.g., 'Axe')")
    advantage: Optional[float] = Field(default=None, description="Win rate advantage % (stats only)")
    games_sampled: Optional[int] = Field(default=None, description="Number of games sampled (stats only)")
    reason: str = Field(description="Explanation of why this hero counters the other")


class HeroCounters(BaseModel):
    """Counter pick data for a single hero."""

    hero_id: int = Field(description="Hero ID")
    hero_name: str = Field(description="Hero internal name")
    localized_name: str = Field(description="Hero display name")
    counters: List[CounterMatchup] = Field(
        default_factory=list,
        description="Heroes that counter this hero (bad against)"
    )
    good_against: List[CounterMatchup] = Field(
        default_factory=list,
        description="Heroes this hero is good against"
    )
    when_to_pick: List[str] = Field(
        default_factory=list,
        description="Conditions/contexts when this hero is strong (lane matchups, team comps, game state)"
    )


class HeroCountersDatabase(BaseModel):
    """Complete counter picks database for all heroes."""

    version: str = Field(description="Version/date of data generation")
    source: str = Field(default="curated", description="Data source (curated or opendota)")
    description: Optional[str] = Field(default=None, description="Database description")
    min_games_threshold: Optional[int] = Field(default=None, description="Minimum games (stats only)")
    min_advantage_threshold: Optional[float] = Field(default=None, description="Minimum advantage % (stats only)")
    heroes: Dict[str, HeroCounters] = Field(
        default_factory=dict,
        description="Counter data keyed by hero_id"
    )


class CounterPickResponse(BaseModel):
    """Response for counter pick queries."""

    hero_id: int = Field(description="Queried hero ID")
    hero_name: str = Field(description="Hero internal name")
    localized_name: str = Field(description="Hero display name")
    counters: List[CounterMatchup] = Field(description="Top heroes that counter this hero")
    good_against: List[CounterMatchup] = Field(description="Top heroes this hero counters")
    total_counters: int = Field(description="Total number of counters in database")
    total_good_against: int = Field(description="Total number of heroes this counters")


class DraftCounterAnalysis(BaseModel):
    """Counter analysis for draft picks."""

    hero_id: int = Field(description="Hero being analyzed")
    hero_name: str = Field(description="Hero internal name")
    localized_name: str = Field(description="Hero display name")
    countered_by_enemy: List[CounterMatchup] = Field(
        default_factory=list,
        description="Enemy heroes that counter this pick"
    )
    counters_enemy: List[CounterMatchup] = Field(
        default_factory=list,
        description="Enemy heroes this pick counters"
    )
    net_advantage: float = Field(
        description="Net advantage against enemy draft (positive = good pick)"
    )


class DraftAnalysisResponse(BaseModel):
    """Complete draft counter analysis."""

    radiant_picks: List[int] = Field(description="Radiant hero IDs")
    dire_picks: List[int] = Field(description="Dire hero IDs")
    radiant_analysis: List[DraftCounterAnalysis] = Field(
        description="Counter analysis for each Radiant hero"
    )
    dire_analysis: List[DraftCounterAnalysis] = Field(
        description="Counter analysis for each Dire hero"
    )
    radiant_net_advantage: float = Field(
        description="Total net advantage for Radiant draft"
    )
    suggested_picks: Optional[List[CounterMatchup]] = Field(
        default=None,
        description="Suggested counter picks if draft is incomplete"
    )
