"""
Tests for timeline parser.
"""

from pathlib import Path

import pytest

from src.utils.timeline_parser import TimelineParser

REAL_MATCH_ID = 8461956309
REPLAY_PATH = Path.home() / "dota2" / "replays" / f"{REAL_MATCH_ID}.dem"


class TestTimelineParser:

    @pytest.fixture
    def parser(self):
        return TimelineParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_parse_timeline_returns_ten_players(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        assert timeline is not None
        assert "players" in timeline
        assert len(timeline["players"]) == 10

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_parse_timeline_has_both_teams(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        radiant = [p for p in timeline["players"] if p["team"] == "radiant"]
        dire = [p for p in timeline["players"] if p["team"] == "dire"]

        assert len(radiant) == 5
        assert len(dire) == 5

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_parse_timeline_has_net_worth_data(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        for player in timeline["players"]:
            assert "net_worth" in player
            assert len(player["net_worth"]) > 0
            assert all(isinstance(v, (int, float)) for v in player["net_worth"])

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_parse_timeline_has_team_graphs(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        assert "radiant" in timeline
        assert "dire" in timeline
        assert "graph_net_worth" in timeline["radiant"]
        assert "graph_net_worth" in timeline["dire"]

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_stats_at_minute_returns_player_stats(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)
        stats = parser.get_stats_at_minute(timeline, 10)

        assert "minute" in stats
        assert stats["minute"] == 10
        assert "players" in stats
        assert len(stats["players"]) == 10

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_stats_at_minute_has_expected_fields(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)
        stats = parser.get_stats_at_minute(timeline, 10)

        for player in stats["players"]:
            assert "player_slot" in player
            assert "team" in player
            assert "net_worth" in player
            assert player["net_worth"] > 0

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_net_worth_increases_over_time(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        for player in timeline["players"]:
            nw = player["net_worth"]
            if len(nw) > 20:
                assert nw[10] < nw[20]

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_parse_timeline_has_last_hits_and_denies(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        for player in timeline["players"]:
            assert "last_hits" in player
            assert "denies" in player
            assert len(player["last_hits"]) > 0
            assert len(player["denies"]) > 0

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_last_hits_increase_over_time(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)

        for player in timeline["players"]:
            lh = player["last_hits"]
            if len(lh) > 10:
                assert lh[5] < lh[10]

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_stats_at_minute_includes_last_hits_denies(self, parser):
        timeline = parser.parse_timeline(REPLAY_PATH)
        stats = parser.get_stats_at_minute(timeline, 5)

        for player in stats["players"]:
            assert "last_hits" in player
            assert "denies" in player
            assert player["last_hits"] >= 0
            assert player["denies"] >= 0
