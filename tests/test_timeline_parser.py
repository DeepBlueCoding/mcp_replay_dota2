"""
Tests for timeline parser.

Uses pre-parsed replay data from conftest.py fixtures.
All data is from match 8461956309.
"""

import pytest


class TestTimelineParser:

    def test_parse_timeline_returns_ten_players(self, timeline):
        assert timeline is not None
        assert "players" in timeline
        assert len(timeline["players"]) == 10

    def test_parse_timeline_has_both_teams(self, timeline):
        radiant = [p for p in timeline["players"] if p["team"] == "radiant"]
        dire = [p for p in timeline["players"] if p["team"] == "dire"]

        assert len(radiant) == 5
        assert len(dire) == 5

    def test_parse_timeline_has_net_worth_data(self, timeline):
        for player in timeline["players"]:
            assert "net_worth" in player
            assert len(player["net_worth"]) > 0
            assert all(isinstance(v, (int, float)) for v in player["net_worth"])

    def test_parse_timeline_has_team_graphs(self, timeline):
        assert "radiant" in timeline
        assert "dire" in timeline
        assert "graph_net_worth" in timeline["radiant"]
        assert "graph_net_worth" in timeline["dire"]

    def test_get_stats_at_minute_returns_player_stats(self, stats_10min):
        assert "minute" in stats_10min
        assert stats_10min["minute"] == 10
        assert "players" in stats_10min
        assert len(stats_10min["players"]) == 10

    def test_get_stats_at_minute_has_expected_fields(self, stats_10min):
        for player in stats_10min["players"]:
            assert "player_slot" in player
            assert "team" in player
            assert "net_worth" in player
            assert player["net_worth"] > 0

    def test_net_worth_increases_over_time(self, timeline):
        for player in timeline["players"]:
            nw = player["net_worth"]
            if len(nw) > 20:
                assert nw[10] < nw[20]

    def test_parse_timeline_has_last_hits_and_denies(self, timeline):
        for player in timeline["players"]:
            assert "last_hits" in player
            assert "denies" in player
            assert len(player["last_hits"]) > 0
            assert len(player["denies"]) > 0

    def test_last_hits_increase_over_time(self, timeline):
        for player in timeline["players"]:
            lh = player["last_hits"]
            if len(lh) > 10:
                assert lh[5] < lh[10]

    def test_get_stats_at_minute_includes_last_hits_denies(self, stats_5min):
        for player in stats_5min["players"]:
            assert "last_hits" in player
            assert "denies" in player
            assert player["last_hits"] >= 0
            assert player["denies"] >= 0
