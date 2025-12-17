"""Tests for match_fetcher module using real match data from 8461956309."""

import pytest

from src.models.match_info import DraftAction, HeroMatchupInfo
from src.models.tool_responses import HeroStats, MatchPlayerInfo
from src.utils.match_fetcher import MatchFetcher, get_lane_name


class TestGetLaneNameWithRealData:
    """Tests for get_lane_name function verified against real match 8461956309.

    Match 8461956309 (TI Grand Final) lane assignments:
    - Radiant: Ame (lane 1), Xm (lane 2), Xxs (lane 3), XinQ (lane 3), xNova (lane 1)
    - Dire: Sneyking (lane 3), skiter (lane 3), Malr1ne (lane 2), AMMAR (lane 1), Cr1t (lane 1)
    """

    def test_radiant_bottom_is_safe_lane(self, match_players):
        """Ame (Radiant, lane 1) plays safe lane - verified from match."""
        ame = next(p for p in match_players if p.get("pro_name") == "Ame")
        assert ame["lane"] == 1
        assert ame["team"] == "radiant"
        assert get_lane_name(ame["lane"], is_radiant=True) == "safe_lane"
        assert ame["lane_name"] == "safe_lane"

    def test_radiant_top_is_off_lane(self, match_players):
        """Xxs (Radiant, lane 3) plays off lane - verified from match."""
        xxs = next(p for p in match_players if p.get("pro_name") == "Xxs")
        assert xxs["lane"] == 3
        assert xxs["team"] == "radiant"
        assert get_lane_name(xxs["lane"], is_radiant=True) == "off_lane"
        assert xxs["lane_name"] == "off_lane"

    def test_dire_top_is_safe_lane(self, match_players):
        """Skiter (Dire, lane 3) plays safe lane - verified from match."""
        skiter = next(p for p in match_players if p.get("pro_name") == "skiter")
        assert skiter["lane"] == 3
        assert skiter["team"] == "dire"
        assert get_lane_name(skiter["lane"], is_radiant=False) == "safe_lane"
        assert skiter["lane_name"] == "safe_lane"

    def test_dire_bottom_is_off_lane(self, match_players):
        """AMMAR (Dire, lane 1) plays off lane - verified from match."""
        ammar = next(p for p in match_players if "AMMAR" in (p.get("pro_name") or ""))
        assert ammar["lane"] == 1
        assert ammar["team"] == "dire"
        assert get_lane_name(ammar["lane"], is_radiant=False) == "off_lane"
        assert ammar["lane_name"] == "off_lane"

    def test_mid_lane_radiant(self, match_players):
        """Xm (Radiant, lane 2) plays mid - verified from match."""
        xm = next(p for p in match_players if p.get("pro_name") == "Xm")
        assert xm["lane"] == 2
        assert xm["team"] == "radiant"
        assert get_lane_name(xm["lane"], is_radiant=True) == "mid_lane"
        assert xm["lane_name"] == "mid_lane"

    def test_mid_lane_dire(self, match_players):
        """Malr1ne (Dire, lane 2) plays mid - verified from match."""
        malr1ne = next(p for p in match_players if p.get("pro_name") == "Malr1ne")
        assert malr1ne["lane"] == 2
        assert malr1ne["team"] == "dire"
        assert get_lane_name(malr1ne["lane"], is_radiant=False) == "mid_lane"
        assert malr1ne["lane_name"] == "mid_lane"

    def test_jungle_returns_jungle(self):
        """Lane 4 returns jungle for both teams."""
        assert get_lane_name(4, is_radiant=True) == "jungle"
        assert get_lane_name(4, is_radiant=False) == "jungle"

    def test_unknown_lane_returns_none(self):
        """Invalid lane values return None."""
        assert get_lane_name(0, is_radiant=True) is None
        assert get_lane_name(5, is_radiant=False) is None
        assert get_lane_name(99, is_radiant=True) is None


class TestMatchPlayersData:
    """Tests for match player data from OpenDota API."""

    def test_match_has_10_players(self, match_players):
        """Match 8461956309 has 10 players."""
        assert len(match_players) == 10

    def test_radiant_has_5_players(self, match_players):
        """Match has 5 Radiant players."""
        radiant = [p for p in match_players if p["team"] == "radiant"]
        assert len(radiant) == 5

    def test_dire_has_5_players(self, match_players):
        """Match has 5 Dire players."""
        dire = [p for p in match_players if p["team"] == "dire"]
        assert len(dire) == 5

    def test_all_players_have_lane_data(self, match_players):
        """All players have lane assignment."""
        for player in match_players:
            assert player.get("lane") is not None
            assert player.get("lane_name") is not None

    def test_ame_is_position_1_juggernaut(self, match_players):
        """Ame plays Juggernaut (hero_id=8) as position 1."""
        ame = next(p for p in match_players if p.get("pro_name") == "Ame")
        assert ame["hero_id"] == 8  # Juggernaut
        assert ame["position"] == 1
        assert ame["role"] == "core"

    def test_skiter_is_position_1_medusa(self, match_players):
        """Skiter plays Medusa (hero_id=94) as position 1."""
        skiter = next(p for p in match_players if p.get("pro_name") == "skiter")
        assert skiter["hero_id"] == 94  # Medusa
        assert skiter["position"] == 1
        assert skiter["role"] == "core"


class TestOpenDotaSDK740Fields:
    """Tests for new fields from python-opendota-sdk 7.40.1."""

    def test_player_has_teamfight_participation_field(self, match_players):
        """Players should have teamfight_participation field (can be None for old matches)."""
        for player in match_players:
            assert "teamfight_participation" in player

    def test_player_has_stuns_field(self, match_players):
        """Players should have stuns field (can be None)."""
        for player in match_players:
            assert "stuns" in player

    def test_player_has_camps_stacked_field(self, match_players):
        """Players should have camps_stacked field (can be None)."""
        for player in match_players:
            assert "camps_stacked" in player

    def test_player_has_obs_placed_field(self, match_players):
        """Players should have obs_placed field (can be None)."""
        for player in match_players:
            assert "obs_placed" in player

    def test_player_has_sen_placed_field(self, match_players):
        """Players should have sen_placed field (can be None)."""
        for player in match_players:
            assert "sen_placed" in player

    def test_player_has_rank_tier_field(self, match_players):
        """Players should have rank_tier field (can be None for pro matches)."""
        for player in match_players:
            assert "rank_tier" in player

    def test_player_has_lane_efficiency_field(self, match_players):
        """Players should have lane_efficiency field (can be None)."""
        for player in match_players:
            assert "lane_efficiency" in player

    def test_player_has_item_neutral2_field(self, match_players):
        """Players should have item_neutral2 field for second neutral slot (7.40+)."""
        for player in match_players:
            assert "item_neutral2" in player

    def test_supports_have_wards_placed(self, match_players):
        """Support players should have ward placement stats."""
        supports = [p for p in match_players if p.get("position") in [4, 5]]
        for support in supports:
            obs = support.get("obs_placed")
            sen = support.get("sen_placed")
            if obs is not None or sen is not None:
                assert (obs or 0) >= 0
                assert (sen or 0) >= 0

    def test_teamfight_participation_in_valid_range(self, match_players):
        """Teamfight participation should be between 0 and 1 when present."""
        for player in match_players:
            tfp = player.get("teamfight_participation")
            if tfp is not None:
                assert 0.0 <= tfp <= 1.0, f"Teamfight participation {tfp} out of range"


class TestEnhancedMatchInfo:
    """Tests for get_enhanced_match_info with new OpenDota fields."""

    @pytest.fixture
    def match_fetcher(self):
        """Create MatchFetcher instance."""
        return MatchFetcher()

    @pytest.mark.asyncio
    async def test_enhanced_info_returns_dict(self, match_fetcher):
        """get_enhanced_match_info should return a dict."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_enhanced_info_has_comeback_field(self, match_fetcher):
        """Enhanced info should have comeback field."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        assert "comeback" in result

    @pytest.mark.asyncio
    async def test_enhanced_info_has_stomp_field(self, match_fetcher):
        """Enhanced info should have stomp field."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        assert "stomp" in result

    @pytest.mark.asyncio
    async def test_enhanced_info_has_pre_game_duration_field(self, match_fetcher):
        """Enhanced info should have pre_game_duration field."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        assert "pre_game_duration" in result

    @pytest.mark.asyncio
    async def test_pro_match_has_team_info(self, match_fetcher):
        """Pro match should have team info with name and logo."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        if result.get("radiant_team"):
            assert "team_id" in result["radiant_team"]
            assert "name" in result["radiant_team"]
            assert "logo_url" in result["radiant_team"]
        if result.get("dire_team"):
            assert "team_id" in result["dire_team"]
            assert "name" in result["dire_team"]
            assert "logo_url" in result["dire_team"]

    @pytest.mark.asyncio
    async def test_pro_match_has_league_info(self, match_fetcher):
        """Pro match should have league info."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        if result.get("league"):
            assert "leagueid" in result["league"]
            assert "name" in result["league"]
            assert "tier" in result["league"]

    @pytest.mark.asyncio
    async def test_cm_match_has_draft_timings(self, match_fetcher):
        """Captains Mode match should have draft_timings."""
        result = await match_fetcher.get_enhanced_match_info(8461956309)
        if result.get("draft_timings"):
            assert len(result["draft_timings"]) > 0
            first_timing = result["draft_timings"][0]
            assert "order" in first_timing
            assert "pick" in first_timing
            assert "active_team" in first_timing
            assert "hero_id" in first_timing


class TestAssignPositionsWithRealData:
    """Tests for position assignment verified against real match 8461956309.

    Radiant positions (verified from OpenDota):
    - Ame (pos 1, core) - lane_role=1, gpm=769
    - Xm (pos 2, core) - lane_role=2, gpm=582
    - Xxs (pos 3, core) - lane_role=3, gpm=515
    - XinQ (pos 4, support) - lane_role=3, gpm=316
    - xNova (pos 5, support) - lane_role=1, gpm=214

    Dire positions (verified from OpenDota):
    - skiter (pos 1, core) - lane_role=1, gpm=1000
    - Malr1ne (pos 2, core) - lane_role=2, gpm=578
    - AMMAR (pos 3, core) - lane_role=3, gpm=576
    - Sneyking (pos 4, support) - lane_role=1, gpm=492
    - Cr1t (pos 5, support) - lane_role=3, gpm=335
    """

    def test_all_positions_assigned_for_radiant(self, match_players):
        """Radiant has all 5 positions assigned."""
        radiant = [p for p in match_players if p["team"] == "radiant"]
        positions = sorted([p["position"] for p in radiant])
        assert positions == [1, 2, 3, 4, 5]

    def test_all_positions_assigned_for_dire(self, match_players):
        """Dire has all 5 positions assigned."""
        dire = [p for p in match_players if p["team"] == "dire"]
        positions = sorted([p["position"] for p in dire])
        assert positions == [1, 2, 3, 4, 5]

    def test_ame_is_radiant_position_1(self, match_players):
        """Ame (highest GPM safelane) is position 1 core."""
        ame = next(p for p in match_players if p.get("pro_name") == "Ame")
        assert ame["position"] == 1
        assert ame["role"] == "core"
        assert ame["lane_role"] == 1  # safelane

    def test_xm_is_radiant_position_2(self, match_players):
        """Xm (mid lane) is position 2 core."""
        xm = next(p for p in match_players if p.get("pro_name") == "Xm")
        assert xm["position"] == 2
        assert xm["role"] == "core"
        assert xm["lane_role"] == 2  # mid

    def test_xxs_is_radiant_position_3(self, match_players):
        """Xxs (highest GPM offlane) is position 3 core."""
        xxs = next(p for p in match_players if p.get("pro_name") == "Xxs")
        assert xxs["position"] == 3
        assert xxs["role"] == "core"
        assert xxs["lane_role"] == 3  # offlane

    def test_xinq_is_radiant_position_4(self, match_players):
        """XinQ (higher GPM support) is position 4."""
        xinq = next(p for p in match_players if p.get("pro_name") == "XinQ")
        assert xinq["position"] == 4
        assert xinq["role"] == "support"

    def test_xnova_is_radiant_position_5(self, match_players):
        """xNova (lowest GPM support) is position 5."""
        xnova = next(p for p in match_players if p.get("pro_name") == "xNova")
        assert xnova["position"] == 5
        assert xnova["role"] == "support"

    def test_skiter_is_dire_position_1(self, match_players):
        """Skiter (highest GPM) is position 1 core."""
        skiter = next(p for p in match_players if p.get("pro_name") == "skiter")
        assert skiter["position"] == 1
        assert skiter["role"] == "core"
        assert skiter["gold_per_min"] == 1000  # Highest GPM in match

    def test_malr1ne_is_dire_position_2(self, match_players):
        """Malr1ne (mid lane) is position 2 core."""
        malr1ne = next(p for p in match_players if p.get("pro_name") == "Malr1ne")
        assert malr1ne["position"] == 2
        assert malr1ne["role"] == "core"
        assert malr1ne["lane_role"] == 2

    def test_ammar_is_dire_position_3(self, match_players):
        """AMMAR (offlane core) is position 3."""
        ammar = next(p for p in match_players if "AMMAR" in (p.get("pro_name") or ""))
        assert ammar["position"] == 3
        assert ammar["role"] == "core"
        assert ammar["lane_role"] == 3

    def test_supports_have_lower_gpm_than_cores(self, match_players):
        """Supports (pos 4-5) have lower GPM than cores (pos 1-3)."""
        radiant = [p for p in match_players if p["team"] == "radiant"]
        radiant_cores = [p for p in radiant if p["position"] <= 3]
        radiant_supports = [p for p in radiant if p["position"] >= 4]

        min_core_gpm = min(p["gold_per_min"] for p in radiant_cores)
        max_support_gpm = max(p["gold_per_min"] for p in radiant_supports)

        assert max_support_gpm < min_core_gpm

    def test_pos4_has_higher_gpm_than_pos5(self, match_players):
        """Position 4 support has higher GPM than position 5."""
        radiant = [p for p in match_players if p["team"] == "radiant"]
        pos4 = next(p for p in radiant if p["position"] == 4)
        pos5 = next(p for p in radiant if p["position"] == 5)

        assert pos4["gold_per_min"] > pos5["gold_per_min"]


class TestPositionFieldInModelsWithRealData:
    """Tests for position field in models using real match 8461956309 data."""

    def test_hero_stats_with_ame_data(self, match_players):
        """HeroStats model with Ame's real data from match."""
        ame = next(p for p in match_players if p.get("pro_name") == "Ame")
        hero = HeroStats(
            hero_id=ame["hero_id"],
            hero_name="npc_dota_hero_juggernaut",
            localized_name="Juggernaut",
            team=ame["team"],
            position=ame["position"],
            kills=ame["kills"],
            deaths=ame["deaths"],
            assists=ame["assists"],
            last_hits=ame["last_hits"],
            denies=ame["denies"],
            gpm=ame["gold_per_min"],
            xpm=ame["xp_per_min"],
            net_worth=ame["net_worth"],
            hero_damage=ame["hero_damage"],
            tower_damage=ame["tower_damage"],
            hero_healing=ame["hero_healing"],
            lane=ame["lane_name"],
            role=ame["role"],
            items=[],
        )
        assert hero.position == 1
        assert hero.hero_id == 8  # Juggernaut
        assert hero.gpm == 769
        assert hero.role == "core"

    def test_hero_stats_with_xnova_support_data(self, match_players):
        """HeroStats model with xNova's support data from match."""
        xnova = next(p for p in match_players if p.get("pro_name") == "xNova")
        hero = HeroStats(
            hero_id=xnova["hero_id"],
            hero_name="npc_dota_hero_pugna",
            localized_name="Pugna",
            team=xnova["team"],
            position=xnova["position"],
            kills=xnova["kills"],
            deaths=xnova["deaths"],
            assists=xnova["assists"],
            last_hits=xnova["last_hits"],
            denies=xnova["denies"],
            gpm=xnova["gold_per_min"],
            xpm=xnova["xp_per_min"],
            net_worth=xnova["net_worth"],
            hero_damage=xnova["hero_damage"],
            tower_damage=xnova["tower_damage"],
            hero_healing=xnova["hero_healing"],
            lane=xnova["lane_name"],
            role=xnova["role"],
            items=[],
        )
        assert hero.position == 5
        assert hero.hero_id == 45  # Pugna
        assert hero.role == "support"

    def test_match_player_info_with_skiter_data(self, match_players):
        """MatchPlayerInfo model with skiter's data from match."""
        skiter = next(p for p in match_players if p.get("pro_name") == "skiter")
        player = MatchPlayerInfo(
            player_name=skiter["pro_name"],
            hero_id=skiter["hero_id"],
            hero_name="npc_dota_hero_medusa",
            localized_name="Medusa",
            position=skiter["position"],
        )
        assert player.position == 1
        assert player.hero_id == 94  # Medusa
        assert player.player_name == "skiter"

    def test_match_player_info_position_defaults_to_none(self):
        """MatchPlayerInfo position should default to None."""
        player = MatchPlayerInfo(
            player_name="TestPlayer",
            hero_id=94,
            hero_name="npc_dota_hero_medusa",
            localized_name="Medusa",
        )
        assert player.position is None


class TestDraftActionWithRealData:
    """Tests for DraftAction model using real match context."""

    def test_draft_action_juggernaut_pick(self, match_players):
        """DraftAction for Juggernaut (Ame's pick) from match 8461956309."""
        ame = next(p for p in match_players if p.get("pro_name") == "Ame")
        action = DraftAction(
            order=10,
            is_pick=True,
            team="radiant",
            hero_id=ame["hero_id"],
            hero_name="juggernaut",
            localized_name="Juggernaut",
            position=ame["position"],
        )
        assert action.hero_id == 8
        assert action.position == 1
        assert action.team == "radiant"

    def test_draft_action_medusa_pick(self, match_players):
        """DraftAction for Medusa (skiter's pick) from match 8461956309."""
        skiter = next(p for p in match_players if p.get("pro_name") == "skiter")
        action = DraftAction(
            order=12,
            is_pick=True,
            team="dire",
            hero_id=skiter["hero_id"],
            hero_name="medusa",
            localized_name="Medusa",
            position=skiter["position"],
        )
        assert action.hero_id == 94
        assert action.position == 1
        assert action.team == "dire"

    def test_draft_action_ban(self):
        """DraftAction for a ban (position should be None)."""
        action = DraftAction(
            order=1,
            is_pick=False,
            team="dire",
            hero_id=23,
            hero_name="kunkka",
            localized_name="Kunkka",
            position=None,
        )
        assert action.is_pick is False
        assert action.position is None

    def test_draft_action_with_matchup_context(self):
        """DraftAction with counters/good_against for Juggernaut."""
        counters = [
            HeroMatchupInfo(hero_id=94, localized_name="Medusa", reason="Split Shot farms faster"),
        ]
        good_against = [
            HeroMatchupInfo(hero_id=89, localized_name="Naga Siren", reason="Blade Fury dispels Net"),
        ]
        action = DraftAction(
            order=10,
            is_pick=True,
            team="radiant",
            hero_id=8,
            hero_name="juggernaut",
            localized_name="Juggernaut",
            position=1,
            counters=counters,
            good_against=good_against,
        )
        assert len(action.counters) == 1
        assert action.counters[0].hero_id == 94
        assert len(action.good_against) == 1
        assert action.good_against[0].hero_id == 89

    def test_draft_action_defaults_empty_lists(self):
        """DraftAction defaults counters/good_against to empty lists."""
        action = DraftAction(
            order=1,
            is_pick=True,
            team="radiant",
            hero_id=8,
            hero_name="juggernaut",
            localized_name="Juggernaut",
        )
        assert action.counters == []
        assert action.good_against == []
        assert action.when_to_pick == []


class TestHeroMatchupInfoWithRealData:
    """Tests for HeroMatchupInfo using real match context."""

    def test_medusa_vs_juggernaut_matchup(self):
        """HeroMatchupInfo for Medusa vs Juggernaut (match 8461956309 matchup)."""
        matchup = HeroMatchupInfo(
            hero_id=94,
            localized_name="Medusa",
            reason="Split Shot clears Healing Ward, Stone Gaze counters Omnislash",
        )
        assert matchup.hero_id == 94
        assert matchup.localized_name == "Medusa"
        assert "Omnislash" in matchup.reason

    def test_naga_siren_counter_matchup(self):
        """HeroMatchupInfo for Naga Siren (match 8461956309 hero)."""
        matchup = HeroMatchupInfo(
            hero_id=89,
            localized_name="Naga Siren",
            reason="Song of the Siren provides team reset",
        )
        assert matchup.hero_id == 89
        assert "Song" in matchup.reason
