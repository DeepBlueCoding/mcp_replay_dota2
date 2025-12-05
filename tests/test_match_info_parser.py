"""
Tests for match info parser.

Uses pre-parsed replay data from conftest.py fixtures.
All data is from match 8461956309 with verified values.
"""


from src.models.match_info import (
    DraftAction,
    DraftResult,
    MatchInfoResult,
    PlayerInfo,
    TeamInfo,
)

# Verified data from match 8461956309 (XG vs FLCN pro match)
REAL_MATCH_ID = 8461956309
EXPECTED_RADIANT_TAG = "XG"
EXPECTED_DIRE_TAG = "FLCN"
EXPECTED_WINNER = "dire"
EXPECTED_GAME_MODE = 2  # Captains Mode
# Note: league_id is not stored in replay files, only on Valve's backend
# The actual league_id from OpenDota API is 18324, but replay parsing returns 0

# Verified draft data (24 actions in CM)
EXPECTED_DRAFT_ACTIONS = 24
EXPECTED_RADIANT_PICKS = ["earthshaker", "shadow_demon", "nevermore", "pugna", "juggernaut"]
EXPECTED_DIRE_PICKS = ["naga_siren", "pangolier", "disruptor", "medusa", "magnataur"]

# Verified player names
EXPECTED_RADIANT_PLAYERS = ["Ame", "Xm", "Xxs", "XinQ", "xNova"]
EXPECTED_DIRE_PLAYERS = ["Sneyking", "skiter", "Malr1ne", "AMMAR_THE_F", "Cr1t-"]


class TestMatchInfoParser:

    def test_get_match_info_returns_match_info_result_model(self, match_info):
        assert match_info is not None
        assert isinstance(match_info, MatchInfoResult)

    def test_get_match_info_correct_match_id(self, match_info):
        assert match_info.match_id == REAL_MATCH_ID

    def test_get_match_info_correct_winner(self, match_info):
        assert match_info.winner == EXPECTED_WINNER

    def test_get_match_info_correct_game_mode(self, match_info):
        assert match_info.game_mode == EXPECTED_GAME_MODE
        assert match_info.game_mode_name == "Captains Mode"

    def test_get_match_info_is_pro_match(self, match_info):
        """Test pro match detection via team_ids (league_id not available in replay files)."""
        assert match_info.is_pro_match is True
        # Note: league_id is not stored in replay files, only on Valve's backend
        # Pro match detection works via team_ids being present
        assert match_info.radiant_team.team_id > 0
        assert match_info.dire_team.team_id > 0

    def test_get_match_info_team_tags(self, match_info):
        assert match_info.radiant_team.team_tag == EXPECTED_RADIANT_TAG
        assert match_info.dire_team.team_tag == EXPECTED_DIRE_TAG

    def test_get_match_info_team_info_structure(self, match_info):
        assert isinstance(match_info.radiant_team, TeamInfo)
        assert isinstance(match_info.dire_team, TeamInfo)
        assert match_info.radiant_team.team_id > 0
        assert match_info.dire_team.team_id > 0

    def test_get_match_info_player_count(self, match_info):
        assert len(match_info.players) == 10
        assert len(match_info.radiant_players) == 5
        assert len(match_info.dire_players) == 5

    def test_get_match_info_player_info_structure(self, match_info):
        for player in match_info.players:
            assert isinstance(player, PlayerInfo)
            assert player.player_name
            assert player.hero_name
            assert player.team in ("radiant", "dire")

    def test_get_match_info_radiant_player_names(self, match_info):
        radiant_names = [p.player_name for p in match_info.radiant_players]
        for expected_name in EXPECTED_RADIANT_PLAYERS:
            assert expected_name in radiant_names

    def test_get_match_info_dire_player_names(self, match_info):
        dire_names = [p.player_name for p in match_info.dire_players]
        for expected_name in EXPECTED_DIRE_PLAYERS:
            assert expected_name in dire_names

    def test_get_match_info_duration_format(self, match_info):
        assert match_info.duration_seconds > 0
        assert ":" in match_info.duration_str
        assert match_info.duration_str == "77:52"


class TestDraftParser:

    def test_get_draft_returns_draft_result_model(self, draft):
        assert draft is not None
        assert isinstance(draft, DraftResult)

    def test_get_draft_correct_match_id(self, draft):
        assert draft.match_id == REAL_MATCH_ID

    def test_get_draft_correct_game_mode(self, draft):
        assert draft.game_mode == EXPECTED_GAME_MODE
        assert draft.game_mode_name == "Captains Mode"

    def test_get_draft_correct_action_count(self, draft):
        assert len(draft.actions) == EXPECTED_DRAFT_ACTIONS

    def test_get_draft_action_structure(self, draft):
        for action in draft.actions:
            assert isinstance(action, DraftAction)
            assert action.order > 0
            assert action.team in ("radiant", "dire")
            assert action.hero_id > 0
            assert action.hero_name
            assert action.localized_name

    def test_get_draft_actions_in_order(self, draft):
        orders = [a.order for a in draft.actions]
        assert orders == list(range(1, EXPECTED_DRAFT_ACTIONS + 1))

    def test_get_draft_radiant_picks(self, draft):
        assert len(draft.radiant_picks) == 5
        radiant_pick_names = [p.hero_name for p in draft.radiant_picks]
        for expected in EXPECTED_RADIANT_PICKS:
            assert expected in radiant_pick_names

    def test_get_draft_dire_picks(self, draft):
        assert len(draft.dire_picks) == 5
        dire_pick_names = [p.hero_name for p in draft.dire_picks]
        for expected in EXPECTED_DIRE_PICKS:
            assert expected in dire_pick_names

    def test_get_draft_ban_counts(self, draft):
        assert len(draft.radiant_bans) == 7
        assert len(draft.dire_bans) == 7

    def test_get_draft_cm_order_preserved(self, draft):
        """Verify CM draft order is preserved (modern CM format)."""
        # First 7 actions should be bans
        for i in range(7):
            assert draft.actions[i].is_pick is False

        # Actions 8-9 should be picks
        for i in range(7, 9):
            assert draft.actions[i].is_pick is True

        # Actions 10-12 should be bans
        for i in range(9, 12):
            assert draft.actions[i].is_pick is False

        # Actions 13-18 should be picks
        for i in range(12, 18):
            assert draft.actions[i].is_pick is True

    def test_get_draft_all_picks_are_picks(self, draft):
        all_picks = draft.radiant_picks + draft.dire_picks
        for pick in all_picks:
            assert pick.is_pick is True

    def test_get_draft_all_bans_are_bans(self, draft):
        all_bans = draft.radiant_bans + draft.dire_bans
        for ban in all_bans:
            assert ban.is_pick is False

    def test_get_draft_first_pick_is_naga_siren(self, draft):
        """First pick in this match was Naga Siren by Dire (action 8)."""
        first_pick = next(a for a in draft.actions if a.is_pick)
        assert first_pick.hero_name == "naga_siren"
        assert first_pick.team == "dire"
        assert first_pick.order == 8
