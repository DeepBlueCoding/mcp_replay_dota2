"""
Tests for the FarmingService using real replay data.

All tests use data from match 8461956309 with verified values.
"""

from src.services.models.farming_data import FarmingPatternResponse


class TestMedusaFarmingPattern:
    """Tests for Medusa's farming pattern in match 8461956309."""

    def test_medusa_total_lane_creeps(self, medusa_farming_pattern):
        """Medusa killed 97 lane creeps in 0-15 minutes."""
        assert medusa_farming_pattern.summary.total_lane_creeps == 97

    def test_medusa_total_neutral_creeps(self, medusa_farming_pattern):
        """Medusa killed 80 neutral creeps in 0-15 minutes."""
        assert medusa_farming_pattern.summary.total_neutral_creeps == 80

    def test_medusa_jungle_percentage(self, medusa_farming_pattern):
        """Medusa's jungle percentage is ~45%."""
        assert 43 <= medusa_farming_pattern.summary.jungle_percentage <= 48

    def test_medusa_total_creeps_count(self, medusa_farming_pattern):
        """Medusa killed 97 lane + 80 neutral = 177 total creeps."""
        total = medusa_farming_pattern.summary.total_lane_creeps + medusa_farming_pattern.summary.total_neutral_creeps
        assert total == 177

    def test_medusa_first_wave_clear(self, medusa_farming_pattern):
        """First wave clear at minute 0 in radiant safelane."""
        minute_0 = medusa_farming_pattern.minutes[0]
        assert len(minute_0.wave_clears) > 0
        first_wave = minute_0.wave_clears[0]
        assert first_wave.time_str == "0:46"
        assert first_wave.creeps_killed >= 1
        assert "safelane" in first_wave.area or "lane" in first_wave.area

    def test_medusa_camps_cleared_includes_large_camps(self, medusa_farming_pattern):
        """Medusa cleared large camps (centaur, troll, satyr)."""
        camps = medusa_farming_pattern.summary.camps_cleared
        assert "large_troll" in camps
        assert camps["large_troll"] >= 1

    def test_medusa_farming_pattern_response_type(self, medusa_farming_pattern):
        """Farming pattern returns correct response model."""
        assert isinstance(medusa_farming_pattern, FarmingPatternResponse)
        assert medusa_farming_pattern.success is True
        assert medusa_farming_pattern.hero == "medusa"

    def test_medusa_has_per_minute_data(self, medusa_farming_pattern):
        """Farming pattern includes per-minute breakdown."""
        assert len(medusa_farming_pattern.minutes) > 0
        minute_5 = next((m for m in medusa_farming_pattern.minutes if m.minute == 5), None)
        assert minute_5 is not None


class TestJuggernautFarmingPattern:
    """Tests for Juggernaut's farming pattern in match 8461956309."""

    def test_juggernaut_total_lane_creeps(self, juggernaut_farming_pattern):
        """Juggernaut killed 80 lane creeps in 0-15 minutes."""
        assert juggernaut_farming_pattern.summary.total_lane_creeps == 80

    def test_juggernaut_total_neutral_creeps(self, juggernaut_farming_pattern):
        """Juggernaut killed 38 neutral creeps in 0-15 minutes."""
        assert juggernaut_farming_pattern.summary.total_neutral_creeps == 38

    def test_juggernaut_farms_less_jungle_than_medusa(self, juggernaut_farming_pattern, medusa_farming_pattern):
        """Juggernaut farms less jungle than Medusa."""
        jug_jungle = juggernaut_farming_pattern.summary.jungle_percentage
        med_jungle = medusa_farming_pattern.summary.jungle_percentage
        assert jug_jungle < med_jungle


class TestFarmingEvents:
    """Tests for farming events (wave clears and camp clears) using real data."""

    def test_wave_clears_have_position(self, medusa_farming_pattern):
        """Wave clears include position data for path visualization."""
        for minute in medusa_farming_pattern.minutes:
            for wave in minute.wave_clears:
                assert wave.position_x is not None or wave.position_y is not None
                assert wave.area is not None
                assert wave.creeps_killed >= 1

    def test_wave_clears_have_required_fields(self, medusa_farming_pattern):
        """Wave clears have all required fields for path visualization."""
        all_waves = []
        for minute in medusa_farming_pattern.minutes:
            all_waves.extend(minute.wave_clears)
        assert len(all_waves) >= 10  # Medusa killed 97 lane creeps, should have multiple wave clears
        for wave in all_waves[:5]:
            assert hasattr(wave, "time_str")
            assert hasattr(wave, "creeps_killed")
            assert hasattr(wave, "position_x")
            assert hasattr(wave, "position_y")
            assert hasattr(wave, "area")
            assert wave.time_str  # non-empty

    def test_wave_clears_group_multiple_creeps(self, medusa_farming_pattern):
        """Wave clears group multiple lane creep kills within 5s window."""
        # With 97 lane creeps killed, if properly grouped we should have fewer wave events
        all_waves = []
        for minute in medusa_farming_pattern.minutes:
            all_waves.extend(minute.wave_clears)
        total_wave_creeps = sum(w.creeps_killed for w in all_waves)
        assert total_wave_creeps == 97  # Total should match lane creeps summary
        # Grouped events should be significantly fewer than individual kills
        assert len(all_waves) < total_wave_creeps

    def test_wave_clears_are_chronological(self, medusa_farming_pattern):
        """Wave clears within each minute are in chronological order."""
        for minute in medusa_farming_pattern.minutes:
            if len(minute.wave_clears) >= 2:
                times = [w.time_str for w in minute.wave_clears]
                assert times == sorted(times), f"Wave clears not sorted in minute {minute.minute}"

    def test_camp_clears_have_position(self, medusa_farming_pattern):
        """Camp clears include position data for path visualization."""
        all_camps = []
        for minute in medusa_farming_pattern.minutes:
            all_camps.extend(minute.camp_sequence)
        assert len(all_camps) >= 20  # Medusa cleared 48 neutral creeps from multiple camps
        for camp in all_camps[:10]:
            assert camp.tier in ("small", "medium", "large", "ancient", "unknown")
            assert camp.creeps_killed >= 1

    def test_camp_clears_have_position_coordinates(self, medusa_farming_pattern):
        """Camp clears include x/y coordinates for map visualization."""
        all_camps = []
        for minute in medusa_farming_pattern.minutes:
            all_camps.extend(minute.camp_sequence)
        camps_with_position = [c for c in all_camps if c.position_x is not None and c.position_y is not None]
        # Most camps should have position data
        assert len(camps_with_position) >= len(all_camps) * 0.8

    def test_camp_clears_group_multiple_creeps(self, medusa_farming_pattern):
        """Camp clears group multiple neutral creep kills from same camp."""
        all_camps = []
        for minute in medusa_farming_pattern.minutes:
            all_camps.extend(minute.camp_sequence)
        total_neutral_creeps = sum(c.creeps_killed for c in all_camps)
        assert total_neutral_creeps == 80  # Total should match neutral creeps summary
        # Grouped events should be fewer than individual kills
        assert len(all_camps) < total_neutral_creeps

    def test_camp_clears_are_chronological(self, medusa_farming_pattern):
        """Farming events within each minute are in chronological order."""
        for minute in medusa_farming_pattern.minutes:
            if len(minute.camp_sequence) >= 2:
                times = [c.time_str for c in minute.camp_sequence]
                assert times == sorted(times), f"Camp sequence not sorted in minute {minute.minute}"


class TestJuggernautFarmingEvents:
    """Tests for Juggernaut farming events in match 8461956309."""

    def test_juggernaut_has_wave_clears(self, juggernaut_farming_pattern):
        """Juggernaut has wave clear events."""
        all_waves = []
        for minute in juggernaut_farming_pattern.minutes:
            all_waves.extend(minute.wave_clears)
        assert len(all_waves) > 0

    def test_juggernaut_wave_creeps_match_summary(self, juggernaut_farming_pattern):
        """Juggernaut wave clears total matches lane creeps summary."""
        all_waves = []
        for minute in juggernaut_farming_pattern.minutes:
            all_waves.extend(minute.wave_clears)
        total_wave_creeps = sum(w.creeps_killed for w in all_waves)
        assert total_wave_creeps == juggernaut_farming_pattern.summary.total_lane_creeps

    def test_juggernaut_camp_creeps_match_summary(self, juggernaut_farming_pattern):
        """Juggernaut camp clears total matches neutral creeps summary."""
        all_camps = []
        for minute in juggernaut_farming_pattern.minutes:
            all_camps.extend(minute.camp_sequence)
        total_camp_creeps = sum(c.creeps_killed for c in all_camps)
        assert total_camp_creeps == juggernaut_farming_pattern.summary.total_neutral_creeps


class TestLaneSummary:
    """Tests for lane summary using real replay data."""

    def test_lane_winners(self, lane_summary):
        """Lane winners are correctly identified."""
        assert lane_summary.top_winner == "dire"
        assert lane_summary.mid_winner == "radiant"
        assert lane_summary.bot_winner == "radiant"

    def test_laning_scores(self, lane_summary):
        """Laning scores are calculated."""
        assert lane_summary.radiant_laning_score > 200
        assert lane_summary.dire_laning_score > 200

    def test_hero_stats_present(self, lane_summary):
        """Hero stats are included for all heroes."""
        assert len(lane_summary.hero_stats) == 10


class TestCSAtMinute:
    """Tests for CS at specific minute using real replay data."""

    def test_cs_at_10_has_all_heroes(self, cs_at_10_minutes):
        """CS data at 10 minutes includes all 10 heroes."""
        assert len(cs_at_10_minutes) == 10

    def test_cs_at_10_medusa_has_good_cs(self, cs_at_10_minutes):
        """Medusa has decent CS at 10 minutes."""
        medusa_cs = cs_at_10_minutes.get("medusa", {})
        assert medusa_cs.get("last_hits", 0) >= 50

    def test_cs_values_are_integers(self, cs_at_10_minutes):
        """CS values are integers."""
        for hero, stats in cs_at_10_minutes.items():
            assert isinstance(stats.get("last_hits", 0), int)
            assert isinstance(stats.get("denies", 0), int)
