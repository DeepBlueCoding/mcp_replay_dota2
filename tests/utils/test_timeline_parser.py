"""Tests for TimelineParser utility."""

from unittest.mock import MagicMock

import pytest

from src.utils.timeline_parser import TimelineParser


class TestTimelineParserUnit:
    """Unit tests for TimelineParser without real replay data."""

    def test_parser_instantiation(self):
        """Test TimelineParser can be instantiated."""
        parser = TimelineParser()
        assert parser is not None

    def test_parse_timeline_no_metadata(self):
        """Test parse_timeline returns None when no metadata."""
        parser = TimelineParser()
        mock_data = MagicMock()
        mock_data.metadata = None

        result = parser.parse_timeline(mock_data)
        assert result is None

    def test_parse_timeline_empty_teams(self):
        """Test parse_timeline returns None when not enough teams."""
        parser = TimelineParser()
        mock_data = MagicMock()
        mock_data.metadata = {"metadata": {"teams": []}}

        result = parser.parse_timeline(mock_data)
        assert result is None

    def test_get_stats_at_minute_empty(self):
        """Test get_stats_at_minute with empty timeline."""
        parser = TimelineParser()
        timeline = {"players": []}

        result = parser.get_stats_at_minute(timeline, 10)
        assert result["minute"] == 10
        assert result["players"] == []


class TestTimelineParserIntegration:
    """Integration tests using real replay data."""

    @pytest.fixture
    def parsed_data(self, parsed_replay_data):
        """Get parsed replay data from conftest fixture."""
        return parsed_replay_data

    def test_parse_timeline_with_real_data(self, parsed_data):
        """Test timeline parsing with real replay data."""
        parser = TimelineParser()
        timeline = parser.parse_timeline(parsed_data)

        # If metadata is available, timeline should work
        if parsed_data.metadata is not None:
            assert timeline is not None
            assert "players" in timeline
            assert "radiant" in timeline
            assert "dire" in timeline
            # Should have 10 players (5 per team)
            assert len(timeline["players"]) == 10
        else:
            # If no metadata, parsing returns None
            assert timeline is None

    def test_get_stats_at_10_minutes(self, parsed_data):
        """Test getting stats at 10 minute mark."""
        parser = TimelineParser()
        timeline = parser.parse_timeline(parsed_data)

        if timeline is not None:
            stats = parser.get_stats_at_minute(timeline, 10)
            assert stats["minute"] == 10
            # Should have stats for all 10 players
            assert len(stats["players"]) == 10
            # Each player should have team info
            for player in stats["players"]:
                assert "team" in player
                assert player["team"] in ["radiant", "dire"]

    def test_timeline_has_net_worth_progression(self, parsed_data):
        """Test that timeline contains net worth progression data."""
        parser = TimelineParser()
        timeline = parser.parse_timeline(parsed_data)

        if timeline is not None:
            for player in timeline["players"]:
                nw = player.get("net_worth", [])
                # Net worth should generally increase over time
                if len(nw) >= 2:
                    # Early game net worth should be less than late game
                    assert nw[-1] >= nw[0], "Net worth should grow over time"

    def test_team_graphs_have_data(self, parsed_data):
        """Test that team graphs contain XP and gold data."""
        parser = TimelineParser()
        timeline = parser.parse_timeline(parsed_data)

        if timeline is not None:
            radiant = timeline.get("radiant", {})
            dire = timeline.get("dire", {})

            # Teams should have graph data
            assert "graph_experience" in radiant or "graph_gold_earned" in radiant
            assert "graph_experience" in dire or "graph_gold_earned" in dire
