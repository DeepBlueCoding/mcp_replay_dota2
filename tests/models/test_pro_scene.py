"""Tests for pro scene Pydantic models."""

from src.models.pro_scene import (
    LeagueInfo,
    ProPlayerInfo,
    RosterEntry,
    SearchResult,
    SeriesSummary,
)


class TestProSceneModels:
    """Tests for pro scene Pydantic models."""

    def test_pro_player_info_creation(self):
        """Test ProPlayerInfo model creation."""
        player = ProPlayerInfo(
            account_id=311360822,
            name="Yatoro",
            personaname="YATORO",
            team_id=8599101,
            team_name="Team Spirit",
            team_tag="Spirit",
            country_code="UA",
            fantasy_role=1,
            is_active=True,
            aliases=["raddan", "illya"],
        )

        assert player.account_id == 311360822
        assert player.name == "Yatoro"
        assert player.team_name == "Team Spirit"
        assert len(player.aliases) == 2

    def test_pro_player_info_with_signature_heroes(self):
        """Test ProPlayerInfo model with signature heroes and role."""
        player = ProPlayerInfo(
            account_id=311360822,
            name="Yatoro",
            personaname="YATORO",
            team_id=8599101,
            team_name="Team Spirit",
            role=1,
            signature_heroes=[
                "npc_dota_hero_morphling",
                "npc_dota_hero_slark",
                "npc_dota_hero_faceless_void",
            ],
            is_active=True,
        )

        assert player.role == 1
        assert len(player.signature_heroes) == 3
        assert "npc_dota_hero_morphling" in player.signature_heroes
        assert "npc_dota_hero_slark" in player.signature_heroes

    def test_pro_player_info_signature_heroes_default_empty(self):
        """Test ProPlayerInfo defaults signature_heroes to empty list."""
        player = ProPlayerInfo(
            account_id=123456,
            name="Unknown Player",
        )

        assert player.signature_heroes == []
        assert player.role is None

    def test_team_info_creation(self):
        """Test TeamInfo model creation."""
        from src.models.pro_scene import TeamInfo

        team = TeamInfo(
            team_id=8599101,
            name="Team Spirit",
            tag="Spirit",
            logo_url="https://example.com/logo.png",
            rating=1500.0,
            wins=100,
            losses=50,
            aliases=["ts", "spirit"],
        )

        assert team.team_id == 8599101
        assert team.name == "Team Spirit"
        assert team.rating == 1500.0
        assert team.wins == 100

    def test_roster_entry_creation(self):
        """Test RosterEntry model creation."""
        entry = RosterEntry(
            account_id=311360822,
            player_name="Yatoro",
            team_id=8599101,
            games_played=150,
            wins=100,
            is_current=True,
        )

        assert entry.account_id == 311360822
        assert entry.games_played == 150
        assert entry.is_current is True

    def test_roster_entry_with_signature_heroes(self):
        """Test RosterEntry model with signature heroes and role."""
        entry = RosterEntry(
            account_id=311360822,
            player_name="Yatoro",
            team_id=8599101,
            role=1,
            signature_heroes=[
                "npc_dota_hero_morphling",
                "npc_dota_hero_faceless_void",
            ],
            games_played=150,
            wins=100,
            is_current=True,
        )

        assert entry.role == 1
        assert len(entry.signature_heroes) == 2
        assert "npc_dota_hero_morphling" in entry.signature_heroes

    def test_search_result_creation(self):
        """Test SearchResult model creation."""
        result = SearchResult(
            id=311360822,
            name="Yatoro",
            matched_alias="raddan",
            similarity=0.85,
        )

        assert result.id == 311360822
        assert result.matched_alias == "raddan"
        assert result.similarity == 0.85

    def test_league_info_creation(self):
        """Test LeagueInfo model creation."""
        league = LeagueInfo(
            league_id=15728,
            name="The International 2023",
            tier="premium",
        )

        assert league.league_id == 15728
        assert league.name == "The International 2023"
        assert league.tier == "premium"

    def test_series_summary_model(self):
        """Test SeriesSummary model creation."""
        series = SeriesSummary(
            series_id=8001,
            series_type=2,
            series_type_name="Bo5",
            team1_id=1100,
            team1_name="Team Spirit",
            team1_wins=3,
            team2_id=1200,
            team2_name="OG",
            team2_wins=2,
            winner_id=1100,
            winner_name="Team Spirit",
            is_complete=True,
            league_id=15728,
            league_name="The International",
            start_time=1699999999,
            games=[],
        )

        assert series.series_id == 8001
        assert series.series_type_name == "Bo5"
        assert series.team1_wins == 3
        assert series.team2_wins == 2
        assert series.winner_name == "Team Spirit"
        assert series.is_complete is True
