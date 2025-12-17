"""Tests for TeamFuzzySearch using real OpenDota team data."""

import pytest

from src.utils.pro_scene_fetcher import pro_scene_fetcher
from src.utils.team_fuzzy_search import TeamFuzzySearch


class TestTeamFuzzySearchWithRealData:
    """Tests for team fuzzy search using real OpenDota team data."""

    @pytest.fixture
    def team_search(self, pro_teams_data) -> TeamFuzzySearch:
        """Create a team fuzzy search with real OpenDota data."""
        search = TeamFuzzySearch()
        aliases = pro_scene_fetcher.get_team_aliases()
        search.initialize(pro_teams_data, aliases)
        return search

    def test_search_team_spirit(self, team_search: TeamFuzzySearch):
        """Find Team Spirit in real data."""
        results = team_search.search("Team Spirit")
        assert len(results) >= 1
        # Team Spirit should be top result
        assert "Spirit" in results[0].name

    def test_search_og(self, team_search: TeamFuzzySearch):
        """Find OG in real data."""
        results = team_search.search("OG")
        assert len(results) >= 1
        assert results[0].name == "OG"

    def test_search_team_liquid(self, team_search: TeamFuzzySearch):
        """Find Team Liquid in real data."""
        results = team_search.search("Team Liquid")
        assert len(results) >= 1
        assert "Liquid" in results[0].name

    def test_search_case_insensitive(self, team_search: TeamFuzzySearch):
        """Search is case insensitive."""
        results = team_search.search("og")
        assert len(results) >= 1
        assert results[0].name == "OG"

    def test_search_by_tag(self, team_search: TeamFuzzySearch):
        """Search by team tag."""
        results = team_search.search("Liquid")
        assert len(results) >= 1

    def test_find_best_match(self, team_search: TeamFuzzySearch):
        """find_best_match returns single result."""
        result = team_search.find_best_match("OG")
        assert result is not None
        assert result.name == "OG"

    def test_search_xtreme_gaming(self, team_search: TeamFuzzySearch):
        """Find Xtreme Gaming (Ame's team from match 8461956309)."""
        results = team_search.search("Xtreme Gaming")
        assert len(results) >= 1


class TestTeamAliases:
    """Tests for team alias resolution using real data."""

    @pytest.fixture
    def team_search(self, pro_teams_data) -> TeamFuzzySearch:
        """Create a team fuzzy search with real OpenDota data and aliases."""
        search = TeamFuzzySearch()
        aliases = pro_scene_fetcher.get_team_aliases()
        search.initialize(pro_teams_data, aliases)
        return search

    def test_bb_alias_finds_betboom(self, team_search: TeamFuzzySearch):
        """'bb' alias finds BetBoom Team."""
        result = team_search.find_best_match("bb")
        assert result is not None
        assert "BetBoom" in result.name
        assert result.id == 8255888

    def test_tl_alias_finds_team_liquid(self, team_search: TeamFuzzySearch):
        """'tl' alias finds Team Liquid."""
        result = team_search.find_best_match("tl")
        assert result is not None
        assert "Liquid" in result.name
        assert result.id == 2163

    def test_flcn_alias_finds_team_falcons(self, team_search: TeamFuzzySearch):
        """'flcn' alias finds Team Falcons."""
        result = team_search.find_best_match("flcn")
        assert result is not None
        assert "Falcons" in result.name
        assert result.id == 9247354

    def test_ngx_alias_finds_nigma_galaxy(self, team_search: TeamFuzzySearch):
        """'ngx' alias finds Nigma Galaxy."""
        result = team_search.find_best_match("ngx")
        assert result is not None
        assert "Nigma" in result.name
        assert result.id == 7554697

    def test_fntc_alias_finds_fnatic(self, team_search: TeamFuzzySearch):
        """'fntc' alias finds Fnatic."""
        result = team_search.find_best_match("fntc")
        assert result is not None
        # Fnatic may have different display name
        assert result.id == 38

    def test_ts_alias_finds_team_spirit(self, team_search: TeamFuzzySearch):
        """'ts' alias finds Team Spirit."""
        result = team_search.find_best_match("ts")
        assert result is not None
        assert "Spirit" in result.name
        assert result.id == 7119388

    def test_eg_alias_finds_evil_geniuses(self, team_search: TeamFuzzySearch):
        """'eg' alias finds Evil Geniuses."""
        result = team_search.find_best_match("eg")
        assert result is not None
        assert result.id == 8255756

    def test_vp_alias_finds_virtus_pro(self, team_search: TeamFuzzySearch):
        """'vp' alias finds Virtus.pro."""
        result = team_search.find_best_match("vp")
        assert result is not None
        # Multiple VP teams exist, just verify name contains Virtus
        assert "Virtus" in result.name or "VP" in result.matched_alias

    def test_navi_alias_finds_natus_vincere(self, team_search: TeamFuzzySearch):
        """'navi' alias finds Natus Vincere."""
        result = team_search.find_best_match("navi")
        assert result is not None
        assert result.id == 36

    def test_xg_alias_finds_xtreme_gaming(self, team_search: TeamFuzzySearch):
        """'xg' alias finds Xtreme Gaming."""
        result = team_search.find_best_match("xg")
        assert result is not None
        assert result.id == 8261500

    def test_sr_alias_finds_shopify_rebellion(self, team_search: TeamFuzzySearch):
        """'sr' alias finds Shopify Rebellion."""
        result = team_search.find_best_match("sr")
        assert result is not None
        assert result.id == 39

    def test_gg_alias_finds_gaimin_gladiators(self, team_search: TeamFuzzySearch):
        """'gg' alias finds Gaimin Gladiators."""
        result = team_search.find_best_match("gg")
        assert result is not None
        assert result.id == 8599101
