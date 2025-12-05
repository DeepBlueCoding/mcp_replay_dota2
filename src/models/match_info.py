"""Pydantic models for match info and draft data."""

from typing import List, Literal

from pydantic import BaseModel, Field


class DraftAction(BaseModel):
    """A single pick or ban in the draft."""

    order: int = Field(description="Draft order (1-24 for CM)")
    is_pick: bool = Field(description="True if pick, False if ban")
    team: Literal["radiant", "dire"] = Field(description="Team making this selection")
    hero_id: int = Field(description="Hero ID")
    hero_name: str = Field(description="Hero internal name (e.g., 'juggernaut')")
    localized_name: str = Field(description="Hero display name (e.g., 'Juggernaut')")


class DraftResult(BaseModel):
    """Complete draft information for a match."""

    match_id: int = Field(description="Match ID")
    game_mode: int = Field(description="Game mode ID (2 = Captains Mode)")
    game_mode_name: str = Field(description="Game mode name")
    actions: List[DraftAction] = Field(description="All draft actions in order")
    radiant_picks: List[DraftAction] = Field(description="Radiant's picked heroes")
    radiant_bans: List[DraftAction] = Field(description="Radiant's banned heroes")
    dire_picks: List[DraftAction] = Field(description="Dire's picked heroes")
    dire_bans: List[DraftAction] = Field(description="Dire's banned heroes")


class TeamInfo(BaseModel):
    """Team information for a match."""

    team_id: int = Field(description="Team ID (0 if not a pro match)")
    team_tag: str = Field(description="Team tag/abbreviation (empty if not pro)")
    team_name: str = Field(description="Full team name (derived from tag or generic)")


class PlayerInfo(BaseModel):
    """Player information in a match."""

    player_name: str = Field(description="Player's display name")
    hero_name: str = Field(description="Hero internal name (e.g., 'juggernaut')")
    hero_localized: str = Field(description="Hero display name (e.g., 'Juggernaut')")
    hero_id: int = Field(description="Hero ID")
    team: Literal["radiant", "dire"] = Field(description="Player's team")
    steam_id: int = Field(description="Player's Steam ID")


class MatchInfoResult(BaseModel):
    """Complete match information from replay."""

    match_id: int = Field(description="Match ID")
    is_pro_match: bool = Field(description="Whether this is a professional match")
    league_id: int = Field(description="League ID (0 if not a league match)")
    game_mode: int = Field(description="Game mode ID")
    game_mode_name: str = Field(description="Game mode name (e.g., 'Captains Mode')")
    winner: Literal["radiant", "dire"] = Field(description="Winning team")
    duration_seconds: float = Field(description="Match duration in seconds")
    duration_str: str = Field(description="Match duration as MM:SS")
    radiant_team: TeamInfo = Field(description="Radiant team info")
    dire_team: TeamInfo = Field(description="Dire team info")
    players: List[PlayerInfo] = Field(description="All 10 players")
    radiant_players: List[PlayerInfo] = Field(description="Radiant's 5 players")
    dire_players: List[PlayerInfo] = Field(description="Dire's 5 players")
