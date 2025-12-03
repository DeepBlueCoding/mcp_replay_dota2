"""Tests for pro scene resources and fuzzy search."""

import pytest

from src.models.pro_scene import (
    LeagueInfo,
    ProMatchSummary,
    ProPlayerInfo,
    RosterEntry,
    SearchResult,
    SeriesSummary,
    TeamInfo,
)
from src.resources.pro_scene_resources import ProSceneResource
from src.utils.player_fuzzy_search import PlayerFuzzySearch
from src.utils.team_fuzzy_search import TeamFuzzySearch


class TestPlayerFuzzySearch:
    """Tests for player fuzzy search."""

    @pytest.fixture
    def player_search(self) -> PlayerFuzzySearch:
        """Create a player fuzzy search instance with test data."""
        search = PlayerFuzzySearch()
        players = [
            {"account_id": 311360822, "name": "Yatoro", "personaname": "YATORO"},
            {"account_id": 139876032, "name": "Miposhka", "personaname": "miposhka"},
            {"account_id": 113331514, "name": "Collapse", "personaname": "Collapse"},
            {"account_id": 312436795, "name": "TorontoTokyo", "personaname": "TT"},
            {"account_id": 111620041, "name": "Miracle-", "personaname": "Miracle"},
            {"account_id": 19672354, "name": "Arteezy", "personaname": "RTZ"},
        ]
        aliases = {
            "311360822": ["raddan", "illya"],
            "19672354": ["rtz", "artour"],
        }
        search.initialize(players, aliases)
        return search

    def test_exact_name_match(self, player_search: PlayerFuzzySearch):
        """Test exact name matching returns similarity 1.0."""
        results = player_search.search("Yatoro")

        assert len(results) >= 1
        assert results[0].name == "Yatoro"
        assert results[0].similarity == 1.0

    def test_case_insensitive_match(self, player_search: PlayerFuzzySearch):
        """Test search is case insensitive."""
        results = player_search.search("yatoro")

        assert len(results) >= 1
        assert results[0].name == "Yatoro"
        assert results[0].similarity == 1.0

    def test_alias_match(self, player_search: PlayerFuzzySearch):
        """Test matching via manual alias."""
        results = player_search.search("raddan")

        assert len(results) >= 1
        assert results[0].id == 311360822
        assert results[0].name == "Yatoro"
        assert results[0].matched_alias == "raddan"
        assert results[0].similarity == 1.0

    def test_partial_match(self, player_search: PlayerFuzzySearch):
        """Test partial name matching."""
        results = player_search.search("miracle")

        assert len(results) >= 1
        assert results[0].id == 111620041

    def test_fuzzy_match(self, player_search: PlayerFuzzySearch):
        """Test fuzzy matching with typos."""
        results = player_search.search("yatorro", threshold=0.7)

        assert len(results) >= 1
        assert results[0].id == 311360822
        assert results[0].similarity >= 0.7

    def test_no_match_below_threshold(self, player_search: PlayerFuzzySearch):
        """Test no results for completely unrelated query."""
        results = player_search.search("xyz123", threshold=0.6)

        assert len(results) == 0

    def test_find_best_match(self, player_search: PlayerFuzzySearch):
        """Test find_best_match returns single result."""
        result = player_search.find_best_match("Collapse")

        assert result is not None
        assert result.id == 113331514
        assert result.name == "Collapse"

    def test_find_best_match_no_match(self, player_search: PlayerFuzzySearch):
        """Test find_best_match returns None for no match."""
        result = player_search.find_best_match("nonexistent_player_xyz")

        assert result is None

    def test_max_results(self, player_search: PlayerFuzzySearch):
        """Test max_results limits output."""
        results = player_search.search("o", threshold=0.3, max_results=3)

        assert len(results) <= 3


class TestTeamFuzzySearch:
    """Tests for team fuzzy search."""

    @pytest.fixture
    def team_search(self) -> TeamFuzzySearch:
        """Create a team fuzzy search instance with test data."""
        search = TeamFuzzySearch()
        teams = [
            {"team_id": 8599101, "name": "Team Spirit", "tag": "Spirit"},
            {"team_id": 7391077, "name": "OG", "tag": "OG"},
            {"team_id": 2163, "name": "Evil Geniuses", "tag": "EG"},
            {"team_id": 1838315, "name": "Team Secret", "tag": "Secret"},
            {"team_id": 39, "name": "Team Liquid", "tag": "Liquid"},
        ]
        aliases = {
            "8599101": ["ts", "spirit"],
            "2163": ["eg"],
            "1838315": ["secret"],
        }
        search.initialize(teams, aliases)
        return search

    def test_exact_name_match(self, team_search: TeamFuzzySearch):
        """Test exact team name matching."""
        results = team_search.search("Team Spirit")

        assert len(results) >= 1
        assert results[0].name == "Team Spirit"
        assert results[0].similarity == 1.0

    def test_tag_match(self, team_search: TeamFuzzySearch):
        """Test matching via team tag."""
        results = team_search.search("Spirit")

        assert len(results) >= 1
        assert results[0].id == 8599101

    def test_alias_match(self, team_search: TeamFuzzySearch):
        """Test matching via team alias."""
        results = team_search.search("ts")

        assert len(results) >= 1
        assert results[0].id == 8599101
        assert results[0].matched_alias == "ts"

    def test_case_insensitive(self, team_search: TeamFuzzySearch):
        """Test case insensitive search."""
        results = team_search.search("og")

        assert len(results) >= 1
        assert results[0].id == 7391077

    def test_partial_match(self, team_search: TeamFuzzySearch):
        """Test partial name matching."""
        results = team_search.search("Evil")

        assert len(results) >= 1
        assert results[0].id == 2163

    def test_find_best_match(self, team_search: TeamFuzzySearch):
        """Test find_best_match returns single result."""
        result = team_search.find_best_match("Liquid")

        assert result is not None
        assert result.id == 39


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

    def test_team_info_creation(self):
        """Test TeamInfo model creation."""
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


class TestSeriesGrouping:
    """Tests for series grouping logic."""

    @pytest.fixture
    def resource(self) -> ProSceneResource:
        """Create a ProSceneResource instance."""
        return ProSceneResource()

    def test_series_type_to_name(self, resource: ProSceneResource):
        """Test series type to name conversion."""
        assert resource._series_type_to_name(0) == "Bo1"
        assert resource._series_type_to_name(1) == "Bo3"
        assert resource._series_type_to_name(2) == "Bo5"

    def test_wins_needed(self, resource: ProSceneResource):
        """Test wins needed calculation."""
        assert resource._wins_needed(0) == 1  # Bo1
        assert resource._wins_needed(1) == 2  # Bo3
        assert resource._wins_needed(2) == 3  # Bo5

    def test_group_matches_bo3_complete(self, resource: ProSceneResource):
        """Test grouping a complete Bo3 series."""
        matches = [
            ProMatchSummary(
                match_id=1001,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=200,
                dire_team_name="Team B",
                radiant_win=True,
                duration=2400,
                start_time=1000,
                series_id=5001,
                series_type=1,  # Bo3
            ),
            ProMatchSummary(
                match_id=1002,
                radiant_team_id=200,
                radiant_team_name="Team B",
                dire_team_id=100,
                dire_team_name="Team A",
                radiant_win=False,
                duration=2200,
                start_time=1100,
                series_id=5001,
                series_type=1,
            ),
        ]

        all_matches, series_list = resource._group_matches_into_series(matches)

        assert len(series_list) == 1
        series = series_list[0]
        assert series.series_id == 5001
        assert series.series_type_name == "Bo3"
        assert series.team1_wins == 2
        assert series.team2_wins == 0
        assert series.winner_id == 100
        assert series.winner_name == "Team A"
        assert series.is_complete is True
        assert len(series.games) == 2
        assert series.games[0].game_number == 1
        assert series.games[1].game_number == 2

    def test_group_matches_bo5_incomplete(self, resource: ProSceneResource):
        """Test grouping an incomplete Bo5 series."""
        matches = [
            ProMatchSummary(
                match_id=2001,
                radiant_team_id=300,
                radiant_team_name="Team X",
                dire_team_id=400,
                dire_team_name="Team Y",
                radiant_win=True,
                duration=2500,
                start_time=2000,
                series_id=6001,
                series_type=2,  # Bo5
            ),
            ProMatchSummary(
                match_id=2002,
                radiant_team_id=400,
                radiant_team_name="Team Y",
                dire_team_id=300,
                dire_team_name="Team X",
                radiant_win=True,
                duration=2300,
                start_time=2100,
                series_id=6001,
                series_type=2,
            ),
        ]

        _, series_list = resource._group_matches_into_series(matches)

        assert len(series_list) == 1
        series = series_list[0]
        assert series.series_type_name == "Bo5"
        assert series.team1_wins == 1
        assert series.team2_wins == 1
        assert series.winner_id is None
        assert series.is_complete is False

    def test_group_matches_standalone(self, resource: ProSceneResource):
        """Test matches without series_id are standalone."""
        matches = [
            ProMatchSummary(
                match_id=3001,
                radiant_team_id=500,
                radiant_team_name="Solo Team",
                dire_team_id=600,
                dire_team_name="Other Team",
                radiant_win=True,
                duration=2100,
                start_time=3000,
                series_id=None,
                series_type=None,
            ),
        ]

        all_matches, series_list = resource._group_matches_into_series(matches)

        assert len(series_list) == 0
        assert len(all_matches) == 1

    def test_group_matches_multiple_series(self, resource: ProSceneResource):
        """Test grouping multiple series correctly."""
        matches = [
            ProMatchSummary(
                match_id=4001,
                radiant_team_id=700,
                radiant_team_name="Alpha",
                dire_team_id=800,
                dire_team_name="Beta",
                radiant_win=True,
                duration=2000,
                start_time=4000,
                series_id=7001,
                series_type=1,
            ),
            ProMatchSummary(
                match_id=4002,
                radiant_team_id=900,
                radiant_team_name="Gamma",
                dire_team_id=1000,
                dire_team_name="Delta",
                radiant_win=False,
                duration=2100,
                start_time=4100,
                series_id=7002,
                series_type=0,  # Bo1
            ),
        ]

        _, series_list = resource._group_matches_into_series(matches)

        assert len(series_list) == 2
        series_ids = {s.series_id for s in series_list}
        assert series_ids == {7001, 7002}

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

    def test_pro_match_summary_with_series_fields(self):
        """Test ProMatchSummary includes series fields."""
        match = ProMatchSummary(
            match_id=9001,
            radiant_team_id=1300,
            radiant_team_name="Gaimin",
            dire_team_id=1400,
            dire_team_name="Tundra",
            radiant_win=True,
            radiant_score=35,
            dire_score=22,
            duration=2800,
            start_time=1700000000,
            league_id=16000,
            league_name="DreamLeague",
            series_id=9001,
            series_type=1,
            game_number=2,
        )

        assert match.series_id == 9001
        assert match.series_type == 1
        assert match.game_number == 2
        assert match.radiant_score == 35
        assert match.dire_score == 22
