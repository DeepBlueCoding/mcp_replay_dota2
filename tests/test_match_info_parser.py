"""
Tests for match info parser.

Uses real replay data from match 8461956309 with verified values.
"""

from pathlib import Path

import pytest

from src.models.match_info import (
    DraftAction,
    DraftResult,
    MatchInfoResult,
    PlayerInfo,
    TeamInfo,
)
from src.utils.match_info_parser import MatchInfoParser

REAL_MATCH_ID = 8461956309
REPLAY_PATH = Path.home() / "dota2" / "replays" / f"{REAL_MATCH_ID}.dem"

# Verified data from match 8461956309 (XG vs FLCN pro match)
EXPECTED_RADIANT_TAG = "XG"
EXPECTED_DIRE_TAG = "FLCN"
EXPECTED_WINNER = "dire"
EXPECTED_GAME_MODE = 2  # Captains Mode
EXPECTED_LEAGUE_ID = 18324

# Verified draft data (24 actions in CM)
EXPECTED_DRAFT_ACTIONS = 24
EXPECTED_RADIANT_PICKS = ["earthshaker", "shadow_demon", "nevermore", "pugna", "juggernaut"]
EXPECTED_DIRE_PICKS = ["naga_siren", "pangolier", "disruptor", "medusa", "magnataur"]

# Verified player names
EXPECTED_RADIANT_PLAYERS = ["Ame", "Xm", "Xxs", "XinQ", "xNova"]
EXPECTED_DIRE_PLAYERS = ["Sneyking", "skiter", "Malr1ne", "AMMAR_THE_F", "Cr1t-"]


class TestMatchInfoParser:

    @pytest.fixture
    def parser(self):
        return MatchInfoParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_returns_match_info_result_model(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result is not None
        assert isinstance(result, MatchInfoResult)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_correct_match_id(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.match_id == REAL_MATCH_ID

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_correct_winner(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.winner == EXPECTED_WINNER

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_correct_game_mode(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.game_mode == EXPECTED_GAME_MODE
        assert result.game_mode_name == "Captains Mode"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_is_pro_match(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.is_pro_match is True
        assert result.league_id == EXPECTED_LEAGUE_ID

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_team_tags(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.radiant_team.team_tag == EXPECTED_RADIANT_TAG
        assert result.dire_team.team_tag == EXPECTED_DIRE_TAG

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_team_info_structure(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert isinstance(result.radiant_team, TeamInfo)
        assert isinstance(result.dire_team, TeamInfo)
        assert result.radiant_team.team_id > 0
        assert result.dire_team.team_id > 0

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_player_count(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert len(result.players) == 10
        assert len(result.radiant_players) == 5
        assert len(result.dire_players) == 5

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_player_info_structure(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        for player in result.players:
            assert isinstance(player, PlayerInfo)
            assert player.player_name
            assert player.hero_name
            assert player.team in ("radiant", "dire")

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_radiant_player_names(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        radiant_names = [p.player_name for p in result.radiant_players]
        for expected_name in EXPECTED_RADIANT_PLAYERS:
            assert expected_name in radiant_names

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_dire_player_names(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        dire_names = [p.player_name for p in result.dire_players]
        for expected_name in EXPECTED_DIRE_PLAYERS:
            assert expected_name in dire_names

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_match_info_duration_format(self, parser):
        result = parser.get_match_info(REPLAY_PATH)

        assert result.duration_seconds > 0
        assert ":" in result.duration_str
        assert result.duration_str == "77:52"


class TestDraftParser:

    @pytest.fixture
    def parser(self):
        return MatchInfoParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_returns_draft_result_model(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert result is not None
        assert isinstance(result, DraftResult)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_correct_match_id(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert result.match_id == REAL_MATCH_ID

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_correct_game_mode(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert result.game_mode == EXPECTED_GAME_MODE
        assert result.game_mode_name == "Captains Mode"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_correct_action_count(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert len(result.actions) == EXPECTED_DRAFT_ACTIONS

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_action_structure(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        for action in result.actions:
            assert isinstance(action, DraftAction)
            assert action.order > 0
            assert action.team in ("radiant", "dire")
            assert action.hero_id > 0
            assert action.hero_name
            assert action.localized_name

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_actions_in_order(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        orders = [a.order for a in result.actions]
        assert orders == list(range(1, EXPECTED_DRAFT_ACTIONS + 1))

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_radiant_picks(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert len(result.radiant_picks) == 5
        radiant_pick_names = [p.hero_name for p in result.radiant_picks]
        for expected in EXPECTED_RADIANT_PICKS:
            assert expected in radiant_pick_names

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_dire_picks(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert len(result.dire_picks) == 5
        dire_pick_names = [p.hero_name for p in result.dire_picks]
        for expected in EXPECTED_DIRE_PICKS:
            assert expected in dire_pick_names

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_ban_counts(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        assert len(result.radiant_bans) == 7
        assert len(result.dire_bans) == 7

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_cm_order_preserved(self, parser):
        """Verify CM draft order is preserved (modern CM format)."""
        result = parser.get_draft(REPLAY_PATH)

        # Modern CM format for this match:
        # 1-7: BANS, 8-9: PICKS, 10-12: BANS, 13-18: PICKS, 19-22: BANS, 23-24: PICKS
        # First 7 actions should be bans
        for i in range(7):
            assert result.actions[i].is_pick is False, f"Action {i+1} should be ban"

        # Actions 8-9 should be picks (Naga Siren, Earthshaker)
        for i in range(7, 9):
            assert result.actions[i].is_pick is True, f"Action {i+1} should be pick"

        # Actions 10-12 should be bans
        for i in range(9, 12):
            assert result.actions[i].is_pick is False, f"Action {i+1} should be ban"

        # Actions 13-18 should be picks
        for i in range(12, 18):
            assert result.actions[i].is_pick is True, f"Action {i+1} should be pick"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_all_picks_are_picks(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        all_picks = result.radiant_picks + result.dire_picks
        for pick in all_picks:
            assert pick.is_pick is True

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_all_bans_are_bans(self, parser):
        result = parser.get_draft(REPLAY_PATH)

        all_bans = result.radiant_bans + result.dire_bans
        for ban in all_bans:
            assert ban.is_pick is False

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_draft_first_pick_is_naga_siren(self, parser):
        """First pick in this match was Naga Siren by Dire (action 8)."""
        result = parser.get_draft(REPLAY_PATH)

        first_pick = next(a for a in result.actions if a.is_pick)
        assert first_pick.hero_name == "naga_siren"
        assert first_pick.team == "dire"
        assert first_pick.order == 8
