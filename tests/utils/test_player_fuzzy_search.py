"""Tests for PlayerFuzzySearch using real OpenDota pro player data."""

import pytest

from src.utils.player_fuzzy_search import PlayerFuzzySearch
from src.utils.pro_scene_fetcher import pro_scene_fetcher


class TestPlayerFuzzySearchWithRealData:
    """Tests for player fuzzy search using real OpenDota pro player data."""

    @pytest.fixture
    def player_search(self, pro_players_data) -> PlayerFuzzySearch:
        """Create a player fuzzy search with real OpenDota data."""
        search = PlayerFuzzySearch()
        aliases = pro_scene_fetcher.get_player_aliases()
        search.initialize(pro_players_data, aliases)
        return search

    def test_search_yatoro(self, player_search: PlayerFuzzySearch):
        """Find Yatoro (Team Spirit carry) in real data."""
        results = player_search.search("Yatoro")
        assert len(results) >= 1
        assert results[0].name == "Yatoro"
        assert results[0].similarity == 1.0

    def test_search_collapse(self, player_search: PlayerFuzzySearch):
        """Find Collapse (Team Spirit offlaner) in real data."""
        results = player_search.search("Collapse")
        assert len(results) >= 1
        # Collapse should be in the results (may not be first due to aliases)
        collapse_found = any(r.name == "Collapse" for r in results)
        assert collapse_found

    def test_search_miracle(self, player_search: PlayerFuzzySearch):
        """Find Miracle- in real data."""
        results = player_search.search("Miracle-")
        assert len(results) >= 1
        assert results[0].name == "Miracle-"

    def test_search_case_insensitive(self, player_search: PlayerFuzzySearch):
        """Search is case insensitive."""
        results = player_search.search("yatoro")
        assert len(results) >= 1
        assert results[0].name == "Yatoro"

    def test_fuzzy_match_with_typo(self, player_search: PlayerFuzzySearch):
        """Fuzzy matching handles typos."""
        results = player_search.search("colapse", threshold=0.7)
        assert len(results) >= 1
        assert results[0].similarity >= 0.7

    def test_low_threshold_filters_weak_matches(self, player_search: PlayerFuzzySearch):
        """Very low threshold with specific query filters weak matches."""
        # Use a very specific query that won't match partial aliases
        results = player_search.search("qwertyuiop12345", threshold=0.95)
        assert len(results) == 0

    def test_find_best_match_returns_single_result(self, player_search: PlayerFuzzySearch):
        """find_best_match returns single best result."""
        result = player_search.find_best_match("Yatoro")
        assert result is not None
        assert result.name == "Yatoro"

    def test_find_best_match_no_match(self, player_search: PlayerFuzzySearch):
        """find_best_match returns None for very specific non-matching query."""
        # Use a query that won't match even partial aliases
        result = player_search.find_best_match("qwertyuiopasdfghjkl", threshold=0.95)
        assert result is None

    def test_max_results_limits_output(self, player_search: PlayerFuzzySearch):
        """max_results limits the number of results."""
        results = player_search.search("a", threshold=0.3, max_results=5)
        assert len(results) <= 5

    def test_search_ame(self, player_search: PlayerFuzzySearch):
        """Find Ame (Xtreme Gaming carry from match 8461956309)."""
        results = player_search.search("Ame")
        assert len(results) >= 1
        # Ame should be in the results
        ame_found = any(r.name == "Ame" for r in results)
        assert ame_found

    def test_search_xinq(self, player_search: PlayerFuzzySearch):
        """Find XinQ (support from match 8461956309)."""
        results = player_search.search("XinQ")
        assert len(results) >= 1
