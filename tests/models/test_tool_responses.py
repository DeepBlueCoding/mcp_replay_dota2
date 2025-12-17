"""Tests for Pydantic tool response models."""

from src.models.tool_responses import (
    KDASnapshot,
    MatchTimelineResponse,
    PlayerStatsAtMinute,
    PlayerTimeline,
    StatsAtMinuteResponse,
    TeamGraphs,
)


class TestTimelineModels:
    """Tests for Pydantic timeline models."""

    def test_kda_snapshot_creation(self):
        """Test KDASnapshot model with all fields."""
        snap = KDASnapshot(
            game_time=600.0,
            kills=5,
            deaths=2,
            assists=10,
            level=12,
        )
        assert snap.game_time == 600.0
        assert snap.kills == 5
        assert snap.deaths == 2
        assert snap.assists == 10
        assert snap.level == 12

    def test_player_timeline_creation(self):
        """Test PlayerTimeline model with timeline data."""
        timeline = PlayerTimeline(
            hero="antimage",
            team="radiant",
            net_worth=[0, 500, 1200, 2500, 4000],
            hero_damage=[0, 100, 300, 800, 1500],
            kda_timeline=[
                KDASnapshot(game_time=0, kills=0, deaths=0, assists=0, level=1),
                KDASnapshot(game_time=300, kills=1, deaths=0, assists=0, level=6),
                KDASnapshot(game_time=600, kills=3, deaths=1, assists=2, level=11),
            ],
        )
        assert timeline.hero == "antimage"
        assert timeline.team == "radiant"
        assert len(timeline.net_worth) == 5
        assert len(timeline.kda_timeline) == 3
        assert timeline.kda_timeline[2].kills == 3

    def test_team_graphs_creation(self):
        """Test TeamGraphs model."""
        graphs = TeamGraphs(
            radiant_xp=[0, 1000, 5000, 12000],
            dire_xp=[0, 900, 4800, 11500],
            radiant_gold=[0, 800, 4000, 10000],
            dire_gold=[0, 750, 3800, 9500],
        )
        assert len(graphs.radiant_xp) == 4
        assert graphs.radiant_xp[3] == 12000
        assert graphs.dire_gold[2] == 3800

    def test_match_timeline_response_success(self):
        """Test successful timeline response."""
        response = MatchTimelineResponse(
            success=True,
            match_id=8461956309,
            players=[
                PlayerTimeline(
                    hero="medusa",
                    team="radiant",
                    net_worth=[0, 500],
                    hero_damage=[0, 100],
                    kda_timeline=[],
                ),
            ],
            team_graphs=TeamGraphs(
                radiant_xp=[0, 1000],
                dire_xp=[0, 900],
                radiant_gold=[0, 800],
                dire_gold=[0, 750],
            ),
        )
        assert response.success is True
        assert response.match_id == 8461956309
        assert len(response.players) == 1
        assert response.team_graphs is not None

    def test_match_timeline_response_error(self):
        """Test timeline response with error."""
        response = MatchTimelineResponse(
            success=False,
            error="No metadata found in replay",
        )
        assert response.success is False
        assert response.error == "No metadata found in replay"
        assert response.players == []
        assert response.team_graphs is None

    def test_player_stats_at_minute(self):
        """Test PlayerStatsAtMinute model."""
        stats = PlayerStatsAtMinute(
            hero="earthshaker",
            team="dire",
            net_worth=4500,
            hero_damage=3200,
            kills=2,
            deaths=1,
            assists=8,
            level=10,
        )
        assert stats.hero == "earthshaker"
        assert stats.team == "dire"
        assert stats.net_worth == 4500
        assert stats.kills == 2
        assert stats.level == 10

    def test_stats_at_minute_response(self):
        """Test StatsAtMinuteResponse model."""
        response = StatsAtMinuteResponse(
            success=True,
            match_id=8461956309,
            minute=10,
            players=[
                PlayerStatsAtMinute(
                    hero="medusa",
                    team="radiant",
                    net_worth=5000,
                    hero_damage=2000,
                    kills=1,
                    deaths=0,
                    assists=2,
                    level=11,
                ),
            ],
        )
        assert response.success is True
        assert response.minute == 10
        assert len(response.players) == 1
