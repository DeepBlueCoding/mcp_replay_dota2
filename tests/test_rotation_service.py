"""
Tests for the RotationService.

Tests lane classification, distance calculation, time formatting, and outcome detection.
These are pure unit tests that don't require replay data.
"""

import pytest

from src.services.models.combat_data import Fight, HeroDeath, RunePickup
from src.services.models.rotation_data import (
    HeroRotationStats,
    PowerRuneEvent,
    Rotation,
    RotationAnalysisResponse,
    RotationOutcome,
    RotationSummary,
    RuneCorrelation,
    RuneRotations,
    WisdomRuneEvent,
)
from src.services.rotation.rotation_service import (
    LANE_BOUNDARIES,
    MIN_ROTATION_DURATION,
    POWER_RUNE_FIRST_SPAWN,
    POWER_RUNE_INTERVAL,
    ROTATION_CORRELATION_WINDOW,
    WISDOM_FIGHT_RADIUS,
    WISDOM_RUNE_FIRST_SPAWN,
    WISDOM_RUNE_INTERVAL,
    RotationService,
)


# Mark all tests in this module as fast (no replay parsing needed)
pytestmark = pytest.mark.fast


class TestConstants:
    """Tests for rotation service constants."""

    def test_power_rune_first_spawn(self):
        """Power runes first spawn at 6:00 (360 seconds)."""
        assert POWER_RUNE_FIRST_SPAWN == 360

    def test_power_rune_interval(self):
        """Power runes spawn every 2 minutes."""
        assert POWER_RUNE_INTERVAL == 120

    def test_wisdom_rune_first_spawn(self):
        """Wisdom runes first spawn at 7:00 (420 seconds)."""
        assert WISDOM_RUNE_FIRST_SPAWN == 420

    def test_wisdom_rune_interval(self):
        """Wisdom runes spawn every 7 minutes."""
        assert WISDOM_RUNE_INTERVAL == 420

    def test_rotation_correlation_window(self):
        """Correlation window is 60 seconds."""
        assert ROTATION_CORRELATION_WINDOW == 60.0

    def test_min_rotation_duration(self):
        """Minimum rotation duration is 15 seconds."""
        assert MIN_ROTATION_DURATION == 15.0

    def test_wisdom_fight_radius(self):
        """Wisdom fight detection radius is 2000 units."""
        assert WISDOM_FIGHT_RADIUS == 2000

    def test_lane_boundaries_exist(self):
        """Lane boundaries are defined for top, mid, and bot."""
        assert "top" in LANE_BOUNDARIES
        assert "mid" in LANE_BOUNDARIES
        assert "bot" in LANE_BOUNDARIES


class TestLaneClassification:
    """Tests for lane classification from position."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_classify_mid_lane_center(self, service):
        """Center of map is mid lane."""
        lane = service._classify_lane(0, 0)
        assert lane == "mid"

    def test_classify_mid_lane_positive_offset(self, service):
        """Slightly positive coordinates still mid lane."""
        lane = service._classify_lane(1000, 1000)
        assert lane == "mid"

    def test_classify_mid_lane_negative_offset(self, service):
        """Slightly negative coordinates still mid lane."""
        lane = service._classify_lane(-1000, -1000)
        assert lane == "mid"

    def test_classify_top_lane(self, service):
        """Top lane is high Y, negative X."""
        lane = service._classify_lane(-4000, 5000)
        assert lane == "top"

    def test_classify_bot_lane(self, service):
        """Bot lane is low Y, positive X."""
        lane = service._classify_lane(4000, -5000)
        assert lane == "bot"

    def test_classify_jungle_radiant(self, service):
        """Radiant jungle (not in any lane) is classified as jungle."""
        # Position between lanes
        lane = service._classify_lane(-5000, -2000)
        assert lane == "jungle"

    def test_classify_jungle_dire(self, service):
        """Dire jungle (not in any lane) is classified as jungle."""
        lane = service._classify_lane(5000, 2000)
        assert lane == "jungle"


class TestTimeFormatting:
    """Tests for time formatting utility."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_format_time_zero(self, service):
        """Zero seconds formats as 0:00."""
        assert service._format_time(0) == "0:00"

    def test_format_time_one_minute(self, service):
        """60 seconds formats as 1:00."""
        assert service._format_time(60) == "1:00"

    def test_format_time_with_seconds(self, service):
        """Mixed minutes and seconds format correctly."""
        assert service._format_time(90) == "1:30"
        assert service._format_time(125) == "2:05"

    def test_format_time_six_minutes(self, service):
        """6:00 is first power rune spawn."""
        assert service._format_time(360) == "6:00"

    def test_format_time_seven_minutes(self, service):
        """7:00 is first wisdom rune spawn."""
        assert service._format_time(420) == "7:00"

    def test_format_time_double_digit_minutes(self, service):
        """Double digit minutes format correctly."""
        assert service._format_time(1234) == "20:34"


class TestHeroNameCleaning:
    """Tests for hero name cleaning utility."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_clean_hero_name_with_prefix(self, service):
        """Removes npc_dota_hero_ prefix."""
        assert service._clean_hero_name("npc_dota_hero_antimage") == "antimage"

    def test_clean_hero_name_without_prefix(self, service):
        """Returns name unchanged if no prefix."""
        assert service._clean_hero_name("antimage") == "antimage"

    def test_clean_hero_name_empty(self, service):
        """Empty string returns empty."""
        assert service._clean_hero_name("") == ""

    def test_clean_hero_name_none(self, service):
        """None returns empty string."""
        assert service._clean_hero_name(None) == ""


class TestDistanceCalculation:
    """Tests for distance calculation utility."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_distance_same_point(self, service):
        """Distance from point to itself is 0."""
        dist = service._distance((100, 200), (100, 200))
        assert dist == 0.0

    def test_distance_horizontal(self, service):
        """Horizontal distance calculation."""
        dist = service._distance((0, 0), (100, 0))
        assert dist == 100.0

    def test_distance_vertical(self, service):
        """Vertical distance calculation."""
        dist = service._distance((0, 0), (0, 100))
        assert dist == 100.0

    def test_distance_diagonal(self, service):
        """Diagonal distance (3-4-5 triangle)."""
        dist = service._distance((0, 0), (300, 400))
        assert dist == 500.0


class TestRuneCorrelation:
    """Tests for finding runes before rotations."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_find_rune_before_rotation_found(self, service):
        """Finds rune picked up 30 seconds before rotation."""
        rune_pickups = [
            RunePickup(
                game_time=330.0,
                game_time_str="5:30",
                tick=10000,
                hero="nevermore",
                rune_type="haste",
            ),
        ]
        result = service._find_rune_before_rotation(
            rune_pickups, "nevermore", rotation_time=360.0
        )
        assert result is not None
        assert result.rune_type == "haste"
        assert result.pickup_time == 330.0
        assert result.seconds_before_rotation == 30.0

    def test_find_rune_before_rotation_too_early(self, service):
        """Does not find rune picked up more than 60 seconds before."""
        rune_pickups = [
            RunePickup(
                game_time=200.0,
                game_time_str="3:20",
                tick=6000,
                hero="nevermore",
                rune_type="haste",
            ),
        ]
        result = service._find_rune_before_rotation(
            rune_pickups, "nevermore", rotation_time=360.0
        )
        assert result is None

    def test_find_rune_before_rotation_after(self, service):
        """Does not find rune picked up after rotation started."""
        rune_pickups = [
            RunePickup(
                game_time=370.0,
                game_time_str="6:10",
                tick=11000,
                hero="nevermore",
                rune_type="haste",
            ),
        ]
        result = service._find_rune_before_rotation(
            rune_pickups, "nevermore", rotation_time=360.0
        )
        assert result is None

    def test_find_rune_before_rotation_wrong_hero(self, service):
        """Does not find rune picked up by different hero."""
        rune_pickups = [
            RunePickup(
                game_time=330.0,
                game_time_str="5:30",
                tick=10000,
                hero="antimage",
                rune_type="haste",
            ),
        ]
        result = service._find_rune_before_rotation(
            rune_pickups, "nevermore", rotation_time=360.0
        )
        assert result is None


class TestFightOutcome:
    """Tests for fight outcome detection."""

    @pytest.fixture
    def service(self):
        return RotationService()

    def test_outcome_no_deaths(self, service):
        """No deaths in window means no engagement."""
        result = service._find_fight_outcome(
            fights=[], deaths=[], hero="nevermore", rotation_time=360.0, to_lane="bot"
        )
        assert result.type == "no_engagement"
        assert result.deaths_in_window == 0

    def test_outcome_kill(self, service):
        """Hero gets a kill without dying."""
        deaths = [
            HeroDeath(
                game_time=370.0,
                game_time_str="6:10",
                tick=11000,
                killer="nevermore",
                victim="antimage",
                killer_is_hero=True,
            ),
        ]
        result = service._find_fight_outcome(
            fights=[], deaths=deaths, hero="nevermore", rotation_time=360.0, to_lane="bot"
        )
        assert result.type == "kill"
        assert result.rotation_hero_died is False
        assert "antimage" in result.kills_by_rotation_hero

    def test_outcome_died(self, service):
        """Hero dies without getting a kill."""
        deaths = [
            HeroDeath(
                game_time=370.0,
                game_time_str="6:10",
                tick=11000,
                killer="antimage",
                victim="nevermore",
                killer_is_hero=True,
            ),
        ]
        result = service._find_fight_outcome(
            fights=[], deaths=deaths, hero="nevermore", rotation_time=360.0, to_lane="bot"
        )
        assert result.type == "died"
        assert result.rotation_hero_died is True
        assert len(result.kills_by_rotation_hero) == 0

    def test_outcome_traded(self, service):
        """Hero gets a kill but also dies."""
        deaths = [
            HeroDeath(
                game_time=370.0,
                game_time_str="6:10",
                tick=11000,
                killer="nevermore",
                victim="antimage",
                killer_is_hero=True,
            ),
            HeroDeath(
                game_time=372.0,
                game_time_str="6:12",
                tick=11100,
                killer="crystal_maiden",
                victim="nevermore",
                killer_is_hero=True,
            ),
        ]
        result = service._find_fight_outcome(
            fights=[], deaths=deaths, hero="nevermore", rotation_time=360.0, to_lane="bot"
        )
        assert result.type == "traded"
        assert result.rotation_hero_died is True
        assert "antimage" in result.kills_by_rotation_hero

    def test_outcome_with_fight_id(self, service):
        """Links to fight_id when fight exists."""
        fights = [
            Fight(
                fight_id="fight_1",
                start_time=365.0,
                end_time=380.0,
                start_time_str="6:05",
                end_time_str="6:20",
                duration=15.0,
                deaths=[],
                participants=["nevermore", "antimage"],
            ),
        ]
        deaths = [
            HeroDeath(
                game_time=370.0,
                game_time_str="6:10",
                tick=11000,
                killer="nevermore",
                victim="antimage",
                killer_is_hero=True,
            ),
        ]
        result = service._find_fight_outcome(
            fights=fights, deaths=deaths, hero="nevermore", rotation_time=360.0, to_lane="bot"
        )
        assert result.fight_id == "fight_1"


class TestPydanticModels:
    """Tests for Pydantic model validation."""

    def test_rotation_model(self):
        """Rotation model validates correctly."""
        rotation = Rotation(
            rotation_id="rot_1",
            hero="nevermore",
            role="mid",
            game_time=360.0,
            game_time_str="6:00",
            from_lane="mid",
            to_lane="bot",
        )
        assert rotation.rotation_id == "rot_1"
        assert rotation.hero == "nevermore"

    def test_rotation_outcome_model(self):
        """RotationOutcome model validates correctly."""
        outcome = RotationOutcome(
            type="kill",
            fight_id="fight_1",
            deaths_in_window=1,
            rotation_hero_died=False,
            kills_by_rotation_hero=["antimage"],
        )
        assert outcome.type == "kill"
        assert outcome.fight_id == "fight_1"

    def test_rune_correlation_model(self):
        """RuneCorrelation model validates correctly."""
        rune = RuneCorrelation(
            rune_type="haste",
            pickup_time=330.0,
            pickup_time_str="5:30",
            seconds_before_rotation=30.0,
        )
        assert rune.rune_type == "haste"
        assert rune.seconds_before_rotation == 30.0

    def test_power_rune_event_model(self):
        """PowerRuneEvent model validates correctly."""
        event = PowerRuneEvent(
            spawn_time=360.0,
            spawn_time_str="6:00",
            location="top",
            taken_by="nevermore",
            pickup_time=362.0,
            led_to_rotation=True,
            rotation_id="rot_1",
        )
        assert event.spawn_time == 360.0
        assert event.led_to_rotation is True

    def test_wisdom_rune_event_model(self):
        """WisdomRuneEvent model validates correctly."""
        event = WisdomRuneEvent(
            spawn_time=420.0,
            spawn_time_str="7:00",
            location="radiant_jungle",
            contested=True,
            fight_id="fight_2",
            deaths_nearby=2,
        )
        assert event.spawn_time == 420.0
        assert event.contested is True

    def test_hero_rotation_stats_model(self):
        """HeroRotationStats model validates correctly."""
        stats = HeroRotationStats(
            hero="nevermore",
            role="mid",
            total_rotations=5,
            successful_ganks=3,
            failed_ganks=1,
            trades=1,
            rune_rotations=4,
        )
        assert stats.total_rotations == 5
        assert stats.successful_ganks == 3

    def test_rotation_summary_model(self):
        """RotationSummary model validates correctly."""
        summary = RotationSummary(
            total_rotations=10,
            runes_leading_to_kills=5,
            wisdom_rune_fights=2,
            most_active_rotator="nevermore",
        )
        assert summary.total_rotations == 10
        assert summary.most_active_rotator == "nevermore"

    def test_rotation_analysis_response_model(self):
        """RotationAnalysisResponse model validates correctly."""
        response = RotationAnalysisResponse(
            success=True,
            match_id=12345,
            start_minute=0,
            end_minute=20,
        )
        assert response.success is True
        assert response.match_id == 12345

    def test_rotation_analysis_response_with_error(self):
        """RotationAnalysisResponse handles error case."""
        response = RotationAnalysisResponse(
            success=False,
            match_id=12345,
            start_minute=0,
            end_minute=20,
            error="Could not parse replay",
        )
        assert response.success is False
        assert response.error == "Could not parse replay"
