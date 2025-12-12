"""Tests for pro scene resources and fuzzy search."""

from unittest.mock import AsyncMock, MagicMock, patch

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
from src.utils.pro_scene_fetcher import pro_scene_fetcher
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


class TestTeamNameResolution:
    """Tests for team name resolution in match responses."""

    @pytest.fixture
    def resource(self) -> ProSceneResource:
        """Create a ProSceneResource instance."""
        return ProSceneResource()

    @pytest.fixture
    def team_lookup(self) -> dict:
        """Create a mock team lookup dictionary."""
        return {
            8261500: "Xtreme Gaming",
            8599101: "Team Spirit",
            7391077: "OG",
            2163: "Evil Geniuses",
            1838315: "Team Secret",
        }

    def test_resolve_team_names_fills_missing_radiant_name(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that missing radiant team name is resolved from lookup."""
        match = ProMatchSummary(
            match_id=8188461851,
            radiant_team_id=8261500,
            radiant_team_name=None,
            dire_team_id=8599101,
            dire_team_name="Team Spirit",
            radiant_win=True,
            duration=2400,
            start_time=1733580000,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name == "Xtreme Gaming"
        assert resolved.dire_team_name == "Team Spirit"

    def test_resolve_team_names_fills_missing_dire_name(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that missing dire team name is resolved from lookup."""
        match = ProMatchSummary(
            match_id=8188461852,
            radiant_team_id=8599101,
            radiant_team_name="Team Spirit",
            dire_team_id=7391077,
            dire_team_name=None,
            radiant_win=False,
            duration=2200,
            start_time=1733580100,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name == "Team Spirit"
        assert resolved.dire_team_name == "OG"

    def test_resolve_team_names_fills_both_missing_names(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that both missing team names are resolved from lookup."""
        match = ProMatchSummary(
            match_id=8188461853,
            radiant_team_id=2163,
            radiant_team_name=None,
            dire_team_id=1838315,
            dire_team_name=None,
            radiant_win=True,
            duration=2600,
            start_time=1733580200,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name == "Evil Geniuses"
        assert resolved.dire_team_name == "Team Secret"

    def test_resolve_team_names_preserves_existing_names(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that existing team names are not overwritten."""
        match = ProMatchSummary(
            match_id=8188461854,
            radiant_team_id=8599101,
            radiant_team_name="Team Spirit",
            dire_team_id=7391077,
            dire_team_name="OG",
            radiant_win=True,
            duration=2500,
            start_time=1733580300,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name == "Team Spirit"
        assert resolved.dire_team_name == "OG"
        assert resolved is match

    def test_resolve_team_names_handles_unknown_team_id(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that unknown team IDs result in None team name."""
        match = ProMatchSummary(
            match_id=8188461855,
            radiant_team_id=9999999,
            radiant_team_name=None,
            dire_team_id=8599101,
            dire_team_name=None,
            radiant_win=False,
            duration=2300,
            start_time=1733580400,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name is None
        assert resolved.dire_team_name == "Team Spirit"

    def test_resolve_team_names_handles_none_team_id(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that None team IDs don't cause errors."""
        match = ProMatchSummary(
            match_id=8188461856,
            radiant_team_id=None,
            radiant_team_name=None,
            dire_team_id=8599101,
            dire_team_name=None,
            radiant_win=True,
            duration=2400,
            start_time=1733580500,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.radiant_team_name is None
        assert resolved.dire_team_name == "Team Spirit"

    def test_resolve_team_names_preserves_all_match_fields(
        self, resource: ProSceneResource, team_lookup: dict
    ):
        """Test that all match fields are preserved after resolution."""
        match = ProMatchSummary(
            match_id=8188461857,
            radiant_team_id=8261500,
            radiant_team_name=None,
            dire_team_id=8599101,
            dire_team_name=None,
            radiant_win=True,
            radiant_score=45,
            dire_score=32,
            duration=2800,
            start_time=1733580600,
            league_id=18324,
            league_name="The International 2025",
            series_id=123456,
            series_type=1,
            game_number=2,
        )

        resolved = resource._resolve_team_names(match, team_lookup)

        assert resolved.match_id == 8188461857
        assert resolved.radiant_team_name == "Xtreme Gaming"
        assert resolved.dire_team_name == "Team Spirit"
        assert resolved.radiant_win is True
        assert resolved.radiant_score == 45
        assert resolved.dire_score == 32
        assert resolved.duration == 2800
        assert resolved.start_time == 1733580600
        assert resolved.league_id == 18324
        assert resolved.league_name == "The International 2025"
        assert resolved.series_id == 123456
        assert resolved.series_type == 1
        assert resolved.game_number == 2


class TestProMatchesDataBlending:
    """Tests for get_pro_matches data blending from multiple sources."""

    @pytest.fixture
    def resource(self) -> ProSceneResource:
        """Create a ProSceneResource instance."""
        return ProSceneResource()

    def test_blending_deduplicates_by_match_id(self, resource: ProSceneResource):
        """Test that matches are deduplicated by match_id when blending."""
        # Create two matches with same ID - should only appear once
        match1 = ProMatchSummary(
            match_id=1001,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )
        match2 = ProMatchSummary(
            match_id=1001,  # Same ID
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        matches_by_id = {match1.match_id: match1}
        if match2.match_id not in matches_by_id:
            matches_by_id[match2.match_id] = match2

        assert len(matches_by_id) == 1

    def test_blending_keeps_team_specific_match_when_duplicate(self, resource: ProSceneResource):
        """Test that team-specific match takes priority over proMatches duplicate."""
        # Team-specific has more detail (league_name)
        team_specific = ProMatchSummary(
            match_id=2001,
            radiant_team_id=100,
            radiant_team_name="Tundra Esports",
            dire_team_id=200,
            dire_team_name="Team Yandex",
            radiant_win=True,
            duration=2400,
            start_time=2000,
            league_name="SLAM V",
        )
        # proMatches may have less detail
        pro_match = ProMatchSummary(
            match_id=2001,  # Same ID
            radiant_team_id=100,
            radiant_team_name="Tundra",  # Different name format
            dire_team_id=200,
            dire_team_name=None,  # Missing
            radiant_win=True,
            duration=2400,
            start_time=2000,
            league_name=None,  # Missing
        )

        # Team-specific goes in first
        matches_by_id = {team_specific.match_id: team_specific}
        # proMatches duplicate is skipped
        if pro_match.match_id not in matches_by_id:
            matches_by_id[pro_match.match_id] = pro_match

        result = matches_by_id[2001]
        assert result.league_name == "SLAM V"
        assert result.radiant_team_name == "Tundra Esports"

    def test_blending_includes_unique_matches_from_both_sources(self, resource: ProSceneResource):
        """Test that unique matches from both sources are included."""
        # Team-specific match
        team_match = ProMatchSummary(
            match_id=3001,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=3000,
        )
        # Different match from proMatches
        pro_match = ProMatchSummary(
            match_id=3002,  # Different ID
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=300,
            dire_team_name="Team C",
            radiant_win=False,
            duration=2200,
            start_time=3100,
        )

        matches_by_id = {team_match.match_id: team_match}
        if pro_match.match_id not in matches_by_id:
            matches_by_id[pro_match.match_id] = pro_match

        assert len(matches_by_id) == 2
        assert 3001 in matches_by_id
        assert 3002 in matches_by_id

    def test_blended_results_sorted_by_start_time_descending(self, resource: ProSceneResource):
        """Test that blended results are sorted by start_time descending."""
        matches = [
            ProMatchSummary(
                match_id=4001,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=200,
                dire_team_name="Team B",
                radiant_win=True,
                duration=2400,
                start_time=1000,  # Oldest
            ),
            ProMatchSummary(
                match_id=4002,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=300,
                dire_team_name="Team C",
                radiant_win=False,
                duration=2200,
                start_time=3000,  # Newest
            ),
            ProMatchSummary(
                match_id=4003,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=400,
                dire_team_name="Team D",
                radiant_win=True,
                duration=2300,
                start_time=2000,  # Middle
            ),
        ]

        sorted_matches = sorted(matches, key=lambda x: x.start_time, reverse=True)

        assert sorted_matches[0].match_id == 4002  # Newest first
        assert sorted_matches[1].match_id == 4003
        assert sorted_matches[2].match_id == 4001  # Oldest last

    def test_blended_results_respect_limit(self, resource: ProSceneResource):
        """Test that blended results respect the limit parameter."""
        matches = [
            ProMatchSummary(
                match_id=5000 + i,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=200,
                dire_team_name="Team B",
                radiant_win=True,
                duration=2400,
                start_time=5000 + i,
            )
            for i in range(10)
        ]

        limit = 5
        limited = sorted(matches, key=lambda x: x.start_time, reverse=True)[:limit]

        assert len(limited) == 5
        assert limited[0].start_time == 5009  # Most recent

    def test_blended_results_apply_days_back_filter(self, resource: ProSceneResource):
        """Test that days_back filter is applied to blended results."""
        import time

        now = int(time.time())
        old_time = now - (10 * 24 * 60 * 60)  # 10 days ago
        recent_time = now - (2 * 24 * 60 * 60)  # 2 days ago
        cutoff = now - (7 * 24 * 60 * 60)  # 7 days ago

        matches = [
            ProMatchSummary(
                match_id=6001,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=200,
                dire_team_name="Team B",
                radiant_win=True,
                duration=2400,
                start_time=old_time,  # Should be filtered out
            ),
            ProMatchSummary(
                match_id=6002,
                radiant_team_id=100,
                radiant_team_name="Team A",
                dire_team_id=300,
                dire_team_name="Team C",
                radiant_win=False,
                duration=2200,
                start_time=recent_time,  # Should be included
            ),
        ]

        filtered = [m for m in matches if m.start_time >= cutoff]

        assert len(filtered) == 1
        assert filtered[0].match_id == 6002


class TestTwoTeamFiltering:
    """Tests for two-team (head-to-head) filtering logic."""

    def test_head_to_head_filter_includes_match_with_both_teams(self):
        """Test that head-to-head filter includes matches where both teams play."""
        match = ProMatchSummary(
            match_id=1001,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        team1_id = 100
        team2_id = 200
        match_team_ids = {match.radiant_team_id, match.dire_team_id}

        assert team1_id in match_team_ids
        assert team2_id in match_team_ids

    def test_head_to_head_filter_excludes_match_without_team1(self):
        """Test that head-to-head filter excludes matches missing team1."""
        match = ProMatchSummary(
            match_id=1002,
            radiant_team_id=300,
            radiant_team_name="Team C",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        team1_id = 100
        match_team_ids = {match.radiant_team_id, match.dire_team_id}

        # Team1 (100) is not in this match - should be excluded
        assert team1_id not in match_team_ids

    def test_head_to_head_filter_excludes_match_without_team2(self):
        """Test that head-to-head filter excludes matches missing team2."""
        match = ProMatchSummary(
            match_id=1003,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=300,
            dire_team_name="Team C",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        team2_id = 200
        match_team_ids = {match.radiant_team_id, match.dire_team_id}

        # Team2 (200) is not in this match - should be excluded
        assert team2_id not in match_team_ids

    def test_head_to_head_works_regardless_of_side(self):
        """Test that head-to-head filter works whether team is radiant or dire."""
        # Team A on radiant, Team B on dire
        match1 = ProMatchSummary(
            match_id=1004,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=200,
            dire_team_name="Team B",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )
        # Team B on radiant, Team A on dire (sides swapped)
        match2 = ProMatchSummary(
            match_id=1005,
            radiant_team_id=200,
            radiant_team_name="Team B",
            dire_team_id=100,
            dire_team_name="Team A",
            radiant_win=False,
            duration=2500,
            start_time=1100,
        )

        team1_id = 100
        team2_id = 200

        # Both matches should pass the filter
        for match in [match1, match2]:
            match_team_ids = {match.radiant_team_id, match.dire_team_id}
            assert team1_id in match_team_ids and team2_id in match_team_ids

    def test_single_team_filter_includes_team_on_radiant(self):
        """Test that single team filter includes matches where team is radiant."""
        match = ProMatchSummary(
            match_id=1006,
            radiant_team_id=100,
            radiant_team_name="Team A",
            dire_team_id=300,
            dire_team_name="Team C",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        team1_id = 100
        assert match.radiant_team_id == team1_id or match.dire_team_id == team1_id

    def test_single_team_filter_includes_team_on_dire(self):
        """Test that single team filter includes matches where team is dire."""
        match = ProMatchSummary(
            match_id=1007,
            radiant_team_id=300,
            radiant_team_name="Team C",
            dire_team_id=100,
            dire_team_name="Team A",
            radiant_win=False,
            duration=2400,
            start_time=1000,
        )

        team1_id = 100
        assert match.radiant_team_id == team1_id or match.dire_team_id == team1_id

    def test_single_team_filter_excludes_unrelated_match(self):
        """Test that single team filter excludes matches without that team."""
        match = ProMatchSummary(
            match_id=1008,
            radiant_team_id=300,
            radiant_team_name="Team C",
            dire_team_id=400,
            dire_team_name="Team D",
            radiant_win=True,
            duration=2400,
            start_time=1000,
        )

        team1_id = 100
        assert match.radiant_team_id != team1_id and match.dire_team_id != team1_id

    def test_no_team_filter_includes_all_matches(self):
        """Test that no team filter includes all matches."""
        matches = [
            ProMatchSummary(
                match_id=1009 + i,
                radiant_team_id=100 + i,
                radiant_team_name=f"Team {i}",
                dire_team_id=200 + i,
                dire_team_name=f"Team {i+10}",
                radiant_win=True,
                duration=2400,
                start_time=1000 + i,
            )
            for i in range(5)
        ]

        team1_id = None
        team2_id = None

        filtered = []
        for match in matches:
            if team1_id and team2_id:
                match_team_ids = {match.radiant_team_id, match.dire_team_id}
                if team1_id not in match_team_ids or team2_id not in match_team_ids:
                    continue
            elif team1_id:
                if match.radiant_team_id != team1_id and match.dire_team_id != team1_id:
                    continue
            filtered.append(match)

        assert len(filtered) == 5


class TestGetProMatchesFiltering:
    """Tests for get_pro_matches filtering with team1_name, team2_name, and other filters."""

    @pytest.fixture
    def resource(self) -> ProSceneResource:
        """Create a ProSceneResource instance."""
        return ProSceneResource()

    @pytest.fixture
    def sample_matches(self) -> list:
        """Create sample matches for filtering tests."""
        return [
            ProMatchSummary(
                match_id=1001,
                radiant_team_id=100,
                radiant_team_name="Team Spirit",
                dire_team_id=200,
                dire_team_name="OG",
                radiant_win=True,
                duration=2400,
                start_time=1700000000,
                league_id=15728,
                league_name="The International 2023",
            ),
            ProMatchSummary(
                match_id=1002,
                radiant_team_id=200,
                radiant_team_name="OG",
                dire_team_id=100,
                dire_team_name="Team Spirit",
                radiant_win=False,
                duration=2200,
                start_time=1700001000,
                league_id=15728,
                league_name="The International 2023",
            ),
            ProMatchSummary(
                match_id=1003,
                radiant_team_id=100,
                radiant_team_name="Team Spirit",
                dire_team_id=300,
                dire_team_name="Team Liquid",
                radiant_win=True,
                duration=2600,
                start_time=1700002000,
                league_id=15728,
                league_name="The International 2023",
            ),
            ProMatchSummary(
                match_id=1004,
                radiant_team_id=200,
                radiant_team_name="OG",
                dire_team_id=300,
                dire_team_name="Team Liquid",
                radiant_win=False,
                duration=2300,
                start_time=1700003000,
                league_id=16000,
                league_name="DreamLeague Season 22",
            ),
            ProMatchSummary(
                match_id=1005,
                radiant_team_id=400,
                radiant_team_name="Tundra",
                dire_team_id=500,
                dire_team_name="Gaimin Gladiators",
                radiant_win=True,
                duration=2500,
                start_time=1700004000,
                league_id=16000,
                league_name="DreamLeague Season 22",
            ),
        ]

    def _apply_team_filters(
        self,
        matches: list,
        team1_id: int | None,
        team2_id: int | None,
    ) -> list:
        """Apply team filtering logic matching the resource implementation."""
        filtered = []
        for match in matches:
            radiant_id = match.radiant_team_id
            dire_id = match.dire_team_id

            if team1_id and team2_id:
                match_team_ids = {radiant_id, dire_id}
                if team1_id not in match_team_ids or team2_id not in match_team_ids:
                    continue
            elif team1_id:
                if radiant_id != team1_id and dire_id != team1_id:
                    continue

            filtered.append(match)
        return filtered

    def test_filter_single_team_returns_all_their_matches(self, sample_matches):
        """Test filtering by single team returns all matches involving that team."""
        team_spirit_id = 100

        filtered = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=None)

        assert len(filtered) == 3
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1002, 1003}

    def test_filter_single_team_og(self, sample_matches):
        """Test filtering by OG returns all OG matches."""
        og_id = 200

        filtered = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=None)

        assert len(filtered) == 3
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1002, 1004}

    def test_filter_head_to_head_spirit_vs_og(self, sample_matches):
        """Test head-to-head filtering returns only matches between both teams."""
        team_spirit_id = 100
        og_id = 200

        filtered = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=og_id)

        assert len(filtered) == 2
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1002}

    def test_filter_head_to_head_spirit_vs_liquid(self, sample_matches):
        """Test head-to-head Spirit vs Liquid returns single match."""
        team_spirit_id = 100
        liquid_id = 300

        filtered = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=liquid_id)

        assert len(filtered) == 1
        assert filtered[0].match_id == 1003

    def test_filter_head_to_head_og_vs_liquid(self, sample_matches):
        """Test head-to-head OG vs Liquid returns single match."""
        og_id = 200
        liquid_id = 300

        filtered = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=liquid_id)

        assert len(filtered) == 1
        assert filtered[0].match_id == 1004

    def test_filter_head_to_head_no_matches(self, sample_matches):
        """Test head-to-head with no common matches returns empty."""
        team_spirit_id = 100
        tundra_id = 400

        filtered = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=tundra_id)

        assert len(filtered) == 0

    def test_filter_no_teams_returns_all(self, sample_matches):
        """Test no team filter returns all matches."""
        filtered = self._apply_team_filters(sample_matches, team1_id=None, team2_id=None)

        assert len(filtered) == 5

    def test_filter_team_order_independent(self, sample_matches):
        """Test that team1/team2 order doesn't affect results."""
        team_spirit_id = 100
        og_id = 200

        filtered1 = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=og_id)
        filtered2 = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=team_spirit_id)

        assert len(filtered1) == len(filtered2)
        assert {m.match_id for m in filtered1} == {m.match_id for m in filtered2}

    def test_filter_combined_with_league_name(self, sample_matches):
        """Test team filter combined with league name filter."""
        og_id = 200
        league_filter = "international"

        # First filter by team
        team_filtered = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=None)

        # Then filter by league
        league_filtered = [
            m for m in team_filtered
            if league_filter.lower() in (m.league_name or "").lower()
        ]

        assert len(league_filtered) == 2
        match_ids = {m.match_id for m in league_filtered}
        assert match_ids == {1001, 1002}

    def test_filter_head_to_head_combined_with_league(self, sample_matches):
        """Test head-to-head filter combined with league filter."""
        team_spirit_id = 100
        og_id = 200
        league_filter = "international"

        # Filter by both teams
        team_filtered = self._apply_team_filters(
            sample_matches, team1_id=team_spirit_id, team2_id=og_id
        )

        # Then filter by league
        league_filtered = [
            m for m in team_filtered
            if league_filter.lower() in (m.league_name or "").lower()
        ]

        assert len(league_filtered) == 2
        match_ids = {m.match_id for m in league_filtered}
        assert match_ids == {1001, 1002}

    def test_filter_single_team_with_dreamleague(self, sample_matches):
        """Test single team filter with DreamLeague matches."""
        og_id = 200
        league_filter = "dreamleague"

        team_filtered = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=None)
        league_filtered = [
            m for m in team_filtered
            if league_filter.lower() in (m.league_name or "").lower()
        ]

        assert len(league_filtered) == 1
        assert league_filtered[0].match_id == 1004

    def test_filter_days_back_logic(self, sample_matches):
        """Test days_back filtering logic."""
        cutoff_time = 1700002500  # Between match 1003 and 1004

        filtered = [m for m in sample_matches if m.start_time >= cutoff_time]

        assert len(filtered) == 2
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1004, 1005}

    def test_filter_team_and_days_back_combined(self, sample_matches):
        """Test combining team filter with days_back."""
        og_id = 200
        cutoff_time = 1700002500

        team_filtered = self._apply_team_filters(sample_matches, team1_id=og_id, team2_id=None)
        time_filtered = [m for m in team_filtered if m.start_time >= cutoff_time]

        assert len(time_filtered) == 1
        assert time_filtered[0].match_id == 1004

    def test_head_to_head_includes_both_sides(self, sample_matches):
        """Test head-to-head includes matches regardless of radiant/dire side."""
        team_spirit_id = 100
        og_id = 200

        filtered = self._apply_team_filters(sample_matches, team1_id=team_spirit_id, team2_id=og_id)

        # Match 1001: Spirit radiant, OG dire
        # Match 1002: OG radiant, Spirit dire
        radiant_teams = {m.radiant_team_id for m in filtered}
        dire_teams = {m.dire_team_id for m in filtered}

        # Both teams appear on both sides
        assert team_spirit_id in radiant_teams
        assert team_spirit_id in dire_teams
        assert og_id in radiant_teams
        assert og_id in dire_teams

    def test_filter_nonexistent_team_returns_empty(self, sample_matches):
        """Test filtering by nonexistent team returns empty list."""
        nonexistent_id = 99999

        filtered = self._apply_team_filters(sample_matches, team1_id=nonexistent_id, team2_id=None)

        assert len(filtered) == 0

    def test_filter_head_to_head_with_one_nonexistent_team(self, sample_matches):
        """Test head-to-head with one nonexistent team returns empty."""
        team_spirit_id = 100
        nonexistent_id = 99999

        filtered = self._apply_team_filters(
            sample_matches, team1_id=team_spirit_id, team2_id=nonexistent_id
        )

        assert len(filtered) == 0


class TestLeagueNameBidirectionalMatching:
    """Tests for bidirectional league name matching in get_pro_matches.

    The league_name filter should match in BOTH directions:
    - "SLAM" matches "SLAM V" (search term in actual)
    - "Blast Slam V" matches "SLAM V" (actual in search term)
    """

    def _apply_league_filter(
        self,
        matches: list,
        league_name: str | None,
    ) -> list:
        """Apply bidirectional league name filter matching resource implementation."""
        if not league_name:
            return matches

        filtered = []
        for match in matches:
            actual_league = (match.league_name or "").lower()
            search_league = league_name.lower()
            # Skip if no league name or no bidirectional match
            if not actual_league:
                continue
            if search_league in actual_league or actual_league in search_league:
                filtered.append(match)
        return filtered

    @pytest.fixture
    def sample_matches_with_leagues(self) -> list:
        """Create sample matches with various league names."""
        return [
            ProMatchSummary(
                match_id=1001,
                radiant_team_id=100,
                radiant_team_name="Tundra Esports",
                dire_team_id=200,
                dire_team_name="Team Yandex",
                radiant_win=True,
                duration=2400,
                start_time=1700000000,
                league_id=17420,
                league_name="SLAM V",  # Short official name
            ),
            ProMatchSummary(
                match_id=1002,
                radiant_team_id=100,
                radiant_team_name="Tundra Esports",
                dire_team_id=300,
                dire_team_name="Team Spirit",
                radiant_win=False,
                duration=2200,
                start_time=1700001000,
                league_id=15728,
                league_name="The International 2023",
            ),
            ProMatchSummary(
                match_id=1003,
                radiant_team_id=400,
                radiant_team_name="OG",
                dire_team_id=500,
                dire_team_name="Gaimin Gladiators",
                radiant_win=True,
                duration=2600,
                start_time=1700002000,
                league_id=16000,
                league_name="DreamLeague Season 22",
            ),
            ProMatchSummary(
                match_id=1004,
                radiant_team_id=100,
                radiant_team_name="Tundra Esports",
                dire_team_id=200,
                dire_team_name="Team Yandex",
                radiant_win=True,
                duration=2300,
                start_time=1700003000,
                league_id=17420,
                league_name="SLAM V",
            ),
            ProMatchSummary(
                match_id=1005,
                radiant_team_id=600,
                radiant_team_name="Team Secret",
                dire_team_id=700,
                dire_team_name="Team Liquid",
                radiant_win=False,
                duration=2500,
                start_time=1700004000,
                league_id=None,
                league_name=None,  # Match without league
            ),
        ]

    def test_search_term_in_actual_league_name(self, sample_matches_with_leagues):
        """Test: 'SLAM' matches 'SLAM V' (search in actual)."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "SLAM")

        assert len(filtered) == 2
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1004}

    def test_actual_league_in_search_term(self, sample_matches_with_leagues):
        """Test: 'Blast Slam V' matches 'SLAM V' (actual in search)."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "Blast Slam V")

        assert len(filtered) == 2
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1004}

    def test_exact_match(self, sample_matches_with_leagues):
        """Test: 'SLAM V' matches 'SLAM V' exactly."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "SLAM V")

        assert len(filtered) == 2
        match_ids = {m.match_id for m in filtered}
        assert match_ids == {1001, 1004}

    def test_case_insensitive_match(self, sample_matches_with_leagues):
        """Test: 'slam v' matches 'SLAM V' case-insensitively."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "slam v")

        assert len(filtered) == 2

    def test_partial_match_dreamleague(self, sample_matches_with_leagues):
        """Test: 'DreamLeague' matches 'DreamLeague Season 22'."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "DreamLeague")

        assert len(filtered) == 1
        assert filtered[0].match_id == 1003

    def test_longer_search_term_matches(self, sample_matches_with_leagues):
        """Test: 'DreamLeague Season 22 Finals' matches 'DreamLeague Season 22'."""
        filtered = self._apply_league_filter(
            sample_matches_with_leagues, "DreamLeague Season 22 Finals"
        )

        assert len(filtered) == 1
        assert filtered[0].match_id == 1003

    def test_no_match_returns_empty(self, sample_matches_with_leagues):
        """Test: 'ESL Pro League' matches nothing."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "ESL Pro League")

        assert len(filtered) == 0

    def test_none_league_filter_returns_all(self, sample_matches_with_leagues):
        """Test: None league filter returns all matches."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, None)

        assert len(filtered) == 5

    def test_empty_string_filter_treated_as_no_filter(self, sample_matches_with_leagues):
        """Test: Empty string filter is treated as no filter (returns all)."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "")

        # Empty string is falsy, so no filtering is applied
        assert len(filtered) == 5

    def test_matches_without_league_excluded(self, sample_matches_with_leagues):
        """Test: Matches without league_name are excluded when filtering."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "SLAM")

        # Match 1005 has league_name=None, should be excluded
        assert 1005 not in {m.match_id for m in filtered}

    def test_international_matches(self, sample_matches_with_leagues):
        """Test: 'International' matches 'The International 2023'."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "International")

        assert len(filtered) == 1
        assert filtered[0].match_id == 1002

    def test_ti_2023_matches(self, sample_matches_with_leagues):
        """Test: 'TI 2023' does NOT match 'The International 2023' (no substring)."""
        filtered = self._apply_league_filter(sample_matches_with_leagues, "TI 2023")

        # "ti 2023" not in "the international 2023" and vice versa
        assert len(filtered) == 0


class TestGetProMatchesWithMockedAPI:
    """Integration tests for get_pro_matches with mocked OpenDota API."""

    @pytest.fixture
    def resource(self) -> ProSceneResource:
        """Create a ProSceneResource instance."""
        return ProSceneResource()

    @pytest.fixture
    def mock_pro_matches_response(self) -> list:
        """Mock response from /proMatches endpoint."""
        return [
            {
                "match_id": 8594217096,
                "radiant_team_id": 8291895,
                "radiant_name": "Tundra Esports",
                "dire_team_id": 9823272,
                "dire_name": "Team Yandex",
                "radiant_win": True,
                "radiant_score": 35,
                "dire_score": 22,
                "duration": 2356,
                "start_time": 1765103486,
                "leagueid": 17420,
                "league_name": "SLAM V",
                "series_id": None,
                "series_type": None,
            },
            {
                "match_id": 8594108564,
                "radiant_team_id": 9823272,
                "radiant_name": "Team Yandex",
                "dire_team_id": 8291895,
                "dire_name": "Tundra Esports",
                "radiant_win": False,
                "radiant_score": 20,
                "dire_score": 40,
                "duration": 2970,
                "start_time": 1765098154,
                "leagueid": 17420,
                "league_name": "SLAM V",
                "series_id": None,
                "series_type": None,
            },
            {
                "match_id": 8590000000,
                "radiant_team_id": 8599101,
                "radiant_name": "Team Spirit",
                "dire_team_id": 7391077,
                "dire_name": "OG",
                "radiant_win": True,
                "radiant_score": 30,
                "dire_score": 25,
                "duration": 2500,
                "start_time": 1765000000,
                "leagueid": 15728,
                "league_name": "The International 2025",
                "series_id": None,
                "series_type": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_league_filter_blast_slam_v_finds_slam_v_matches(
        self, resource: ProSceneResource, mock_pro_matches_response: list
    ):
        """Test that 'Blast Slam V' finds matches with league_name='SLAM V'."""
        # Mock the OpenDota client context manager
        mock_client = MagicMock()
        mock_client.get_pro_matches = AsyncMock(return_value=mock_pro_matches_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.resources.pro_scene_resources.OpenDota", return_value=mock_client):
            with patch.object(resource, "_build_team_lookup", new_callable=AsyncMock, return_value={}):
                with patch.object(resource, "_ensure_initialized", new_callable=AsyncMock):
                    result = await resource.get_pro_matches(
                        limit=100,
                        league_name="Blast Slam V",  # User searches with full name
                    )

        assert result.success is True
        assert result.total_matches == 2  # Only SLAM V matches

        match_ids = {m.match_id for m in result.matches}
        assert 8594217096 in match_ids
        assert 8594108564 in match_ids
        assert 8590000000 not in match_ids  # TI match excluded

    @pytest.mark.asyncio
    async def test_league_filter_slam_finds_slam_v_matches(
        self, resource: ProSceneResource, mock_pro_matches_response: list
    ):
        """Test that 'SLAM' finds matches with league_name='SLAM V'."""
        mock_client = MagicMock()
        mock_client.get_pro_matches = AsyncMock(return_value=mock_pro_matches_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.resources.pro_scene_resources.OpenDota", return_value=mock_client):
            with patch.object(resource, "_build_team_lookup", new_callable=AsyncMock, return_value={}):
                with patch.object(resource, "_ensure_initialized", new_callable=AsyncMock):
                    result = await resource.get_pro_matches(
                        limit=100,
                        league_name="SLAM",
                    )

        assert result.success is True
        assert result.total_matches == 2

    @pytest.mark.asyncio
    async def test_league_filter_international_finds_ti_matches(
        self, resource: ProSceneResource, mock_pro_matches_response: list
    ):
        """Test that 'International' finds TI matches."""
        mock_client = MagicMock()
        mock_client.get_pro_matches = AsyncMock(return_value=mock_pro_matches_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.resources.pro_scene_resources.OpenDota", return_value=mock_client):
            with patch.object(resource, "_build_team_lookup", new_callable=AsyncMock, return_value={}):
                with patch.object(resource, "_ensure_initialized", new_callable=AsyncMock):
                    result = await resource.get_pro_matches(
                        limit=100,
                        league_name="International",
                    )

        assert result.success is True
        assert result.total_matches == 1
        assert result.matches[0].match_id == 8590000000

    @pytest.mark.asyncio
    async def test_no_league_filter_returns_all_matches(
        self, resource: ProSceneResource, mock_pro_matches_response: list
    ):
        """Test that no league filter returns all matches."""
        mock_client = MagicMock()
        mock_client.get_pro_matches = AsyncMock(return_value=mock_pro_matches_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.resources.pro_scene_resources.OpenDota", return_value=mock_client):
            with patch.object(resource, "_build_team_lookup", new_callable=AsyncMock, return_value={}):
                with patch.object(resource, "_ensure_initialized", new_callable=AsyncMock):
                    result = await resource.get_pro_matches(limit=100)

        assert result.success is True
        assert result.total_matches == 3

    @pytest.mark.asyncio
    async def test_nonexistent_league_returns_empty(
        self, resource: ProSceneResource, mock_pro_matches_response: list
    ):
        """Test that searching for nonexistent league returns no matches."""
        mock_client = MagicMock()
        mock_client.get_pro_matches = AsyncMock(return_value=mock_pro_matches_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.resources.pro_scene_resources.OpenDota", return_value=mock_client):
            with patch.object(resource, "_build_team_lookup", new_callable=AsyncMock, return_value={}):
                with patch.object(resource, "_ensure_initialized", new_callable=AsyncMock):
                    result = await resource.get_pro_matches(
                        limit=100,
                        league_name="ESL Pro League",
                    )

        assert result.success is True
        assert result.total_matches == 0


class TestSignatureHeroes:
    """Tests for signature heroes data loading."""

    def test_load_signature_heroes_data(self):
        """Test that signature heroes data can be loaded from file."""
        data = pro_scene_fetcher.get_player_signature_heroes()

        assert isinstance(data, dict)
        assert len(data) > 0

    def test_signature_heroes_excludes_metadata(self):
        """Test that metadata keys starting with _ are excluded."""
        data = pro_scene_fetcher.get_player_signature_heroes()

        for key in data:
            assert not key.startswith("_")

    def test_yatoro_signature_heroes(self):
        """Test Yatoro's signature heroes are correctly loaded."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        yatoro = data.get("311360822")

        assert yatoro is not None
        assert yatoro["name"] == "Yatoro"
        assert yatoro["role"] == 1
        assert "npc_dota_hero_morphling" in yatoro["signature_heroes"]
        assert "npc_dota_hero_slark" in yatoro["signature_heroes"]

    def test_collapse_signature_heroes(self):
        """Test Collapse's signature heroes as pos 3."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        collapse = data.get("113331514")

        assert collapse is not None
        assert collapse["name"] == "Collapse"
        assert collapse["role"] == 3
        assert "npc_dota_hero_mars" in collapse["signature_heroes"]
        assert "npc_dota_hero_magnataur" in collapse["signature_heroes"]

    def test_miposhka_signature_heroes(self):
        """Test Miposhka's signature heroes as pos 5."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        miposhka = data.get("139876032")

        assert miposhka is not None
        assert miposhka["name"] == "Miposhka"
        assert miposhka["role"] == 5
        assert len(miposhka["signature_heroes"]) >= 3

    def test_pure_signature_heroes(self):
        """Test Pure's signature heroes as pos 1."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        pure = data.get("168803634")

        assert pure is not None
        assert pure["name"] == "Pure"
        assert pure["role"] == 1
        assert "npc_dota_hero_faceless_void" in pure["signature_heroes"]
        assert "npc_dota_hero_terrorblade" in pure["signature_heroes"]
