"""Pydantic models for pro scene data (players, teams, leagues)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ProPlayerInfo(BaseModel):
    """Pro player with enriched data."""

    account_id: int = Field(description="Player's Steam account ID")
    name: str = Field(description="Professional name")
    personaname: Optional[str] = Field(default=None, description="Steam persona name")
    team_id: Optional[int] = Field(default=None, description="Current team ID")
    team_name: Optional[str] = Field(default=None, description="Current team name")
    team_tag: Optional[str] = Field(default=None, description="Current team tag")
    country_code: Optional[str] = Field(default=None, description="Country code")
    fantasy_role: Optional[int] = Field(
        default=None, description="Fantasy role (1=Core, 2=Support)"
    )
    role: Optional[int] = Field(
        default=None, description="Position (1=carry, 2=mid, 3=offlane, 4=soft support, 5=hard support)"
    )
    signature_heroes: List[str] = Field(
        default_factory=list,
        description="Signature heroes this player is known for (internal names like npc_dota_hero_morphling)"
    )
    is_active: bool = Field(default=True, description="Whether player is currently active")
    aliases: List[str] = Field(default_factory=list, description="Known aliases")


class TeamInfo(BaseModel):
    """Team with enriched data."""

    team_id: int = Field(description="Team ID")
    name: str = Field(description="Team name")
    tag: str = Field(description="Team tag/abbreviation")
    logo_url: Optional[str] = Field(default=None, description="Team logo URL")
    rating: float = Field(default=0.0, description="Team rating/ELO")
    wins: int = Field(default=0, description="Total wins")
    losses: int = Field(default=0, description="Total losses")
    aliases: List[str] = Field(default_factory=list, description="Known aliases")


class RosterEntry(BaseModel):
    """A player's tenure on a team."""

    account_id: int = Field(description="Player account ID")
    player_name: str = Field(description="Player's pro name")
    team_id: int = Field(description="Team ID")
    role: Optional[int] = Field(
        default=None, description="Position (1=carry, 2=mid, 3=offlane, 4=soft support, 5=hard support)"
    )
    signature_heroes: List[str] = Field(
        default_factory=list,
        description="Signature heroes this player is known for (internal names)"
    )
    games_played: int = Field(default=0, description="Games with this team")
    wins: int = Field(default=0, description="Wins with this team")
    is_current: bool = Field(default=False, description="Currently on this team")


class LeagueInfo(BaseModel):
    """League/tournament information."""

    league_id: int = Field(description="League ID")
    name: str = Field(description="League name")
    tier: Optional[str] = Field(
        default=None, description="Tier (premium, professional, amateur)"
    )


class ProMatchSummary(BaseModel):
    """Summary of a pro match for tournament context."""

    match_id: int = Field(description="Match ID")
    radiant_team_id: Optional[int] = Field(default=None, description="Radiant team ID")
    radiant_team_name: Optional[str] = Field(default=None, description="Radiant team name")
    dire_team_id: Optional[int] = Field(default=None, description="Dire team ID")
    dire_team_name: Optional[str] = Field(default=None, description="Dire team name")
    radiant_win: bool = Field(description="Did radiant win")
    radiant_score: int = Field(default=0, description="Radiant kills")
    dire_score: int = Field(default=0, description="Dire kills")
    duration: int = Field(description="Match duration in seconds")
    start_time: int = Field(description="Unix timestamp of match start")
    league_id: Optional[int] = Field(default=None, description="League ID")
    league_name: Optional[str] = Field(default=None, description="League name")
    series_id: Optional[int] = Field(default=None, description="Series ID for grouping")
    series_type: Optional[int] = Field(
        default=None, description="Series type: 0=Bo1, 1=Bo3, 2=Bo5"
    )
    game_number: Optional[int] = Field(
        default=None, description="Game number within series (1, 2, 3...)"
    )


class SeriesSummary(BaseModel):
    """Summary of a series (Bo1, Bo3, Bo5)."""

    series_id: int = Field(description="Series ID")
    series_type: int = Field(description="Series type: 0=Bo1, 1=Bo3, 2=Bo5")
    series_type_name: str = Field(description="Human readable: Bo1, Bo3, Bo5")
    team1_id: Optional[int] = Field(default=None, description="First team ID")
    team1_name: Optional[str] = Field(default=None, description="First team name")
    team1_wins: int = Field(default=0, description="Games won by team 1")
    team2_id: Optional[int] = Field(default=None, description="Second team ID")
    team2_name: Optional[str] = Field(default=None, description="Second team name")
    team2_wins: int = Field(default=0, description="Games won by team 2")
    winner_id: Optional[int] = Field(default=None, description="Winning team ID")
    winner_name: Optional[str] = Field(default=None, description="Winning team name")
    is_complete: bool = Field(default=False, description="Whether series is complete")
    league_id: Optional[int] = Field(default=None, description="League ID")
    league_name: Optional[str] = Field(default=None, description="League name")
    start_time: int = Field(default=0, description="Unix timestamp of first game")
    games: List[ProMatchSummary] = Field(
        default_factory=list, description="Individual games in the series"
    )


class SearchResult(BaseModel):
    """A fuzzy search result."""

    id: int = Field(
        description="Entity ID (account_id for players, team_id for teams)"
    )
    name: str = Field(description="Entity name")
    matched_alias: str = Field(description="The alias that matched")
    similarity: float = Field(description="Similarity score 0.0-1.0")


class PlayerSearchResponse(BaseModel):
    """Response for player search tool."""

    success: bool
    query: str
    total_results: int = Field(default=0)
    results: List[SearchResult] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class TeamSearchResponse(BaseModel):
    """Response for team search tool."""

    success: bool
    query: str
    total_results: int = Field(default=0)
    results: List[SearchResult] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class ProPlayerResponse(BaseModel):
    """Response for get_pro_player tool."""

    success: bool
    player: Optional[ProPlayerInfo] = Field(default=None)
    error: Optional[str] = Field(default=None)


class TeamResponse(BaseModel):
    """Response for get_team tool."""

    success: bool
    team: Optional[TeamInfo] = Field(default=None)
    roster: List[RosterEntry] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class TeamMatchesResponse(BaseModel):
    """Response for get_team_matches tool."""

    success: bool
    team_id: int
    team_name: Optional[str] = Field(default=None)
    total_matches: int = Field(default=0)
    matches: List[ProMatchSummary] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class LeaguesResponse(BaseModel):
    """Response for get_leagues tool."""

    success: bool
    total_leagues: int = Field(default=0)
    leagues: List[LeagueInfo] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)


class ProMatchesResponse(BaseModel):
    """Response for get_pro_matches tool."""

    success: bool
    total_matches: int = Field(default=0)
    total_series: int = Field(default=0)
    matches: List[ProMatchSummary] = Field(default_factory=list)
    series: List[SeriesSummary] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)
    message: Optional[str] = Field(default=None)


class LeagueMatchesResponse(BaseModel):
    """Response for get_league_matches tool."""

    success: bool
    league_id: int
    league_name: Optional[str] = Field(default=None)
    total_matches: int = Field(default=0)
    total_series: int = Field(default=0)
    matches: List[ProMatchSummary] = Field(default_factory=list)
    series: List[SeriesSummary] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)
