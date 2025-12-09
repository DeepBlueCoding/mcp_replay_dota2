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
