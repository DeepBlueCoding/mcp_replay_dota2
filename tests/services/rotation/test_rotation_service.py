"""
Tests for RotationService using real match data.

All tests verify actual rotation detection results from test matches.
"""

import pytest

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


@pytest.fixture(scope="module")
def rotation_service():
    """RotationService instance."""
    return RotationService()


@pytest.fixture(scope="module")
def rotation_analysis(parsed_replay_data, rotation_service):
    """Rotation analysis for match 8461956309 (0-20 min)."""
    return rotation_service.get_rotation_analysis(
        parsed_replay_data, start_minute=0, end_minute=20
    )


@pytest.fixture(scope="module")
def rotation_analysis_2(parsed_replay_data_2, rotation_service):
    """Rotation analysis for match 8594217096 (0-20 min)."""
    return rotation_service.get_rotation_analysis(
        parsed_replay_data_2, start_minute=0, end_minute=20
    )


class TestRotationServiceConstants:
    """Tests for rotation service constants."""

    def test_power_rune_first_spawn_at_6_minutes(self):
        """Power runes first spawn at 6:00 (360 seconds)."""
        assert POWER_RUNE_FIRST_SPAWN == 360

    def test_power_rune_interval_is_2_minutes(self):
        """Power runes spawn every 2 minutes."""
        assert POWER_RUNE_INTERVAL == 120

    def test_wisdom_rune_first_spawn_at_7_minutes(self):
        """Wisdom runes first spawn at 7:00 (420 seconds)."""
        assert WISDOM_RUNE_FIRST_SPAWN == 420

    def test_wisdom_rune_interval_is_7_minutes(self):
        """Wisdom runes spawn every 7 minutes."""
        assert WISDOM_RUNE_INTERVAL == 420

    def test_rotation_correlation_window_is_60_seconds(self):
        """Correlation window is 60 seconds."""
        assert ROTATION_CORRELATION_WINDOW == 60.0

    def test_min_rotation_duration_is_15_seconds(self):
        """Minimum rotation duration is 15 seconds."""
        assert MIN_ROTATION_DURATION == 15.0

    def test_wisdom_fight_radius_is_2000_units(self):
        """Wisdom fight detection radius is 2000 units."""
        assert WISDOM_FIGHT_RADIUS == 2000

    def test_lane_boundaries_defined(self):
        """Lane boundaries are defined for top, mid, and bot."""
        assert "top" in LANE_BOUNDARIES
        assert "mid" in LANE_BOUNDARIES
        assert "bot" in LANE_BOUNDARIES


class TestMatch8461956309Rotations:
    """Tests for rotation analysis on match 8461956309."""

    def test_analysis_succeeds(self, rotation_analysis):
        """Rotation analysis succeeds for match 8461956309."""
        assert rotation_analysis.success is True
        assert rotation_analysis.match_id == 8461956309

    def test_detects_29_rotations(self, rotation_analysis):
        """Match 8461956309 has 29 rotations detected in first 20 minutes."""
        assert rotation_analysis.summary.total_rotations == 29

    def test_shadow_demon_is_most_active_rotator(self, rotation_analysis):
        """Shadow Demon is the most active rotator with 7 rotations."""
        assert rotation_analysis.summary.most_active_rotator == "shadow_demon"
        stats = rotation_analysis.summary.by_hero.get("shadow_demon")
        assert stats is not None
        assert stats.total_rotations == 7

    def test_shadow_demon_has_7_rotations(self, rotation_analysis):
        """Shadow Demon made 7 rotations."""
        stats = rotation_analysis.summary.by_hero.get("shadow_demon")
        assert stats is not None
        assert stats.total_rotations == 7

    def test_pugna_rotates_from_bot_to_mid(self, rotation_analysis):
        """Pugna rotated from bot to mid at 6:00."""
        pugna_rotations = [
            r for r in rotation_analysis.rotations
            if r.hero == "pugna" and r.game_time == 360.0
        ]
        assert len(pugna_rotations) >= 1
        assert pugna_rotations[0].from_lane == "bot"
        assert pugna_rotations[0].to_lane == "mid"

    def test_earthshaker_has_4_rotations(self, rotation_analysis):
        """Earthshaker made 4 rotations."""
        stats = rotation_analysis.summary.by_hero.get("earthshaker")
        assert stats is not None
        assert stats.total_rotations == 4

    def test_juggernaut_no_rotations(self, rotation_analysis):
        """Juggernaut (carry) made 0 rotations - stayed in lane."""
        stats = rotation_analysis.summary.by_hero.get("juggernaut")
        assert stats is not None
        assert stats.total_rotations == 0

    def test_pangolier_has_successful_gank(self, rotation_analysis):
        """Pangolier has 1 successful gank."""
        stats = rotation_analysis.summary.by_hero.get("pangolier")
        assert stats is not None
        assert stats.successful_ganks == 1

    def test_power_runes_tracked(self, rotation_analysis):
        """Power rune events are tracked."""
        assert rotation_analysis.rune_events is not None
        assert len(rotation_analysis.rune_events.power_runes) >= 10

    def test_naga_siren_took_6_00_rune(self, rotation_analysis):
        """Naga Siren took a power rune at 6:00."""
        runes_at_6 = [
            r for r in rotation_analysis.rune_events.power_runes
            if r.spawn_time == 360.0 and r.taken_by == "naga_siren"
        ]
        assert len(runes_at_6) >= 1


class TestMatch8594217096Rotations:
    """Tests for rotation analysis on match 8594217096."""

    def test_analysis_succeeds(self, rotation_analysis_2):
        """Rotation analysis succeeds for match 8594217096."""
        assert rotation_analysis_2.success is True

    def test_detects_36_rotations(self, rotation_analysis_2):
        """Match 8594217096 has 36 rotations detected in first 20 minutes."""
        assert rotation_analysis_2.summary.total_rotations == 36

    def test_juggernaut_is_most_active_rotator(self, rotation_analysis_2):
        """Juggernaut is the most active rotator in match 2."""
        assert rotation_analysis_2.summary.most_active_rotator == "juggernaut"

    def test_batrider_has_early_rotation(self, rotation_analysis_2):
        """Batrider has early rotation detected."""
        bat_rotations = [
            r for r in rotation_analysis_2.rotations
            if r.hero == "batrider" and r.game_time <= 60.0
        ]
        assert len(bat_rotations) >= 1

    def test_pugna_has_early_rotation(self, rotation_analysis_2):
        """Pugna has early rotation detected."""
        pugna_rotations = [
            r for r in rotation_analysis_2.rotations
            if r.hero == "pugna" and r.game_time <= 60.0
        ]
        assert len(pugna_rotations) >= 1


class TestRotationResponseModel:
    """Tests for rotation response model structure."""

    def test_rotations_have_required_fields(self, rotation_analysis):
        """Each rotation has all required fields."""
        for rot in rotation_analysis.rotations[:5]:
            assert rot.rotation_id is not None
            assert rot.hero is not None
            assert rot.game_time >= 0
            assert rot.game_time_str is not None
            assert rot.from_lane in ["top", "mid", "bot", "jungle"]
            assert rot.to_lane in ["top", "mid", "bot", "jungle"]

    def test_rotations_have_outcome(self, rotation_analysis):
        """Each rotation has an outcome."""
        for rot in rotation_analysis.rotations[:5]:
            assert rot.outcome is not None
            assert rot.outcome.type in ["kill", "died", "traded", "no_engagement"]

    def test_rotations_sorted_by_time(self, rotation_analysis):
        """Rotations are sorted by game time."""
        times = [r.game_time for r in rotation_analysis.rotations]
        assert times == sorted(times)

    def test_summary_has_by_hero_stats(self, rotation_analysis):
        """Summary includes per-hero rotation stats."""
        assert rotation_analysis.summary.by_hero is not None
        assert len(rotation_analysis.summary.by_hero) == 10  # All 10 heroes

    def test_hero_stats_have_required_fields(self, rotation_analysis):
        """Each hero's stats has required fields."""
        for hero, stats in rotation_analysis.summary.by_hero.items():
            assert stats.hero == hero
            assert stats.total_rotations >= 0
            assert stats.successful_ganks >= 0
            assert stats.failed_ganks >= 0


class TestUtilityFunctions:
    """Tests for utility functions using real match context."""

    def test_format_time_6_00(self, rotation_service):
        """6:00 is first power rune spawn."""
        assert rotation_service._format_time(360) == "6:00"

    def test_format_time_7_00(self, rotation_service):
        """7:00 is first wisdom rune spawn."""
        assert rotation_service._format_time(420) == "7:00"

    def test_clean_hero_name_removes_prefix(self, rotation_service):
        """Removes npc_dota_hero_ prefix."""
        assert rotation_service._clean_hero_name("npc_dota_hero_shadow_demon") == "shadow_demon"

    def test_classify_lane_mid(self, rotation_service):
        """Center of map classifies as mid."""
        assert rotation_service._classify_lane(0, 0) == "mid"

    def test_classify_lane_top(self, rotation_service):
        """Top-left area classifies as top lane."""
        assert rotation_service._classify_lane(-4000, 5000) == "top"

    def test_classify_lane_bot(self, rotation_service):
        """Bottom-right area classifies as bot lane."""
        assert rotation_service._classify_lane(4000, -5000) == "bot"
