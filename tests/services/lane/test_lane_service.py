"""
Tests for enhanced LaneService functionality.

Tests the new lane analysis features:
- Last hits and denies with positions
- Harass/trading detection
- Tower proximity timeline
- Rotation detection (smoke, TP, twin gate)
- Wave nuke detection
"""

import pytest

from src.services.lane.lane_service import LaneService
from src.services.models.lane_data import (
    HeroLanePhase,
    HeroPosition,
    LaneHarass,
    LaneLastHit,
    LaneRotation,
    LaneSummaryResponse,
    TowerProximityEvent,
    WaveNuke,
)


@pytest.fixture(scope="module")
def lane_svc():
    """LaneService instance."""
    return LaneService()


class TestLaneLastHits:
    """Tests for get_lane_last_hits functionality."""

    def test_returns_list_of_lane_last_hit(self, lane_svc, parsed_replay_data):
        """Returns list of LaneLastHit models."""
        last_hits = lane_svc.get_lane_last_hits(parsed_replay_data)
        assert isinstance(last_hits, list)
        if last_hits:
            assert isinstance(last_hits[0], LaneLastHit)

    def test_last_hits_have_required_fields(self, lane_svc, parsed_replay_data):
        """Each last hit has required fields."""
        last_hits = lane_svc.get_lane_last_hits(parsed_replay_data)
        for lh in last_hits[:10]:
            assert lh.game_time >= 0
            assert lh.game_time_str
            assert lh.hero
            assert lh.target
            assert lh.lane in ["top", "mid", "bot", "jungle", "unknown"]

    def test_last_hits_sorted_by_time(self, lane_svc, parsed_replay_data):
        """Last hits are sorted chronologically."""
        last_hits = lane_svc.get_lane_last_hits(parsed_replay_data)
        times = [lh.game_time for lh in last_hits]
        assert times == sorted(times)

    def test_last_hits_filter_by_hero(self, lane_svc, parsed_replay_data):
        """Can filter last hits by hero."""
        all_lh = lane_svc.get_lane_last_hits(parsed_replay_data)
        medusa_lh = lane_svc.get_lane_last_hits(parsed_replay_data, hero_filter="medusa")
        assert len(medusa_lh) < len(all_lh)
        for lh in medusa_lh:
            assert "medusa" in lh.hero.lower()

    def test_denies_detected(self, lane_svc, parsed_replay_data):
        """Denies are detected with is_deny=True."""
        last_hits = lane_svc.get_lane_last_hits(parsed_replay_data)
        denies = [lh for lh in last_hits if lh.is_deny]
        assert len(denies) > 0  # At least some denies in a 10 min game

    def test_last_hits_have_positions(self, lane_svc, parsed_replay_data):
        """Last hits include position coordinates."""
        last_hits = lane_svc.get_lane_last_hits(parsed_replay_data)
        with_pos = [lh for lh in last_hits if lh.position_x is not None]
        assert len(with_pos) > len(last_hits) * 0.8  # Most have positions


class TestLaneHarass:
    """Tests for get_lane_harass functionality."""

    def test_returns_list_of_lane_harass(self, lane_svc, parsed_replay_data):
        """Returns list of LaneHarass models."""
        harass = lane_svc.get_lane_harass(parsed_replay_data)
        assert isinstance(harass, list)
        if harass:
            assert isinstance(harass[0], LaneHarass)

    def test_harass_events_have_required_fields(self, lane_svc, parsed_replay_data):
        """Each harass event has required fields."""
        harass = lane_svc.get_lane_harass(parsed_replay_data)
        for h in harass[:10]:
            assert h.game_time >= 0
            assert h.game_time_str
            assert h.attacker
            assert h.target
            assert h.damage > 0

    def test_harass_sorted_by_time(self, lane_svc, parsed_replay_data):
        """Harass events are sorted chronologically."""
        harass = lane_svc.get_lane_harass(parsed_replay_data)
        times = [h.game_time for h in harass]
        assert times == sorted(times)

    def test_harass_filter_by_hero(self, lane_svc, parsed_replay_data):
        """Can filter harass by hero."""
        all_harass = lane_svc.get_lane_harass(parsed_replay_data)
        es_harass = lane_svc.get_lane_harass(parsed_replay_data, hero_filter="earthshaker")
        assert len(es_harass) < len(all_harass)
        for h in es_harass:
            assert "earthshaker" in h.attacker.lower() or "earthshaker" in h.target.lower()

    def test_harass_includes_ability_info(self, lane_svc, parsed_replay_data):
        """Some harass events include ability name."""
        harass = lane_svc.get_lane_harass(parsed_replay_data)
        with_ability = [h for h in harass if h.ability is not None]
        assert len(with_ability) > 0  # Some ability harass


class TestTowerProximity:
    """Tests for get_tower_proximity_timeline functionality."""

    def test_returns_list_of_tower_events(self, lane_svc, parsed_replay_data):
        """Returns list of TowerProximityEvent models."""
        events = lane_svc.get_tower_proximity_timeline(parsed_replay_data)
        assert isinstance(events, list)
        if events:
            assert isinstance(events[0], TowerProximityEvent)

    def test_tower_events_have_required_fields(self, lane_svc, parsed_replay_data):
        """Each tower event has required fields."""
        events = lane_svc.get_tower_proximity_timeline(parsed_replay_data)
        for e in events[:10]:
            assert e.game_time >= 0
            assert e.game_time_str
            assert e.hero
            assert e.tower_team in ["radiant", "dire"]
            assert e.event_type in ["entered", "left"]

    def test_tower_events_sorted_by_time(self, lane_svc, parsed_replay_data):
        """Tower events are sorted chronologically."""
        events = lane_svc.get_tower_proximity_timeline(parsed_replay_data)
        times = [e.game_time for e in events]
        assert times == sorted(times)

    def test_tower_events_filter_by_hero(self, lane_svc, parsed_replay_data):
        """Can filter tower events by hero."""
        all_events = lane_svc.get_tower_proximity_timeline(parsed_replay_data)
        hero_events = lane_svc.get_tower_proximity_timeline(parsed_replay_data, hero_filter="medusa")
        if all_events:
            assert len(hero_events) <= len(all_events)
            for e in hero_events:
                assert "medusa" in e.hero.lower()


class TestWaveNukes:
    """Tests for get_wave_nukes functionality."""

    def test_returns_list_of_wave_nukes(self, lane_svc, parsed_replay_data):
        """Returns list of WaveNuke models."""
        nukes = lane_svc.get_wave_nukes(parsed_replay_data)
        assert isinstance(nukes, list)
        if nukes:
            assert isinstance(nukes[0], WaveNuke)

    def test_wave_nukes_have_required_fields(self, lane_svc, parsed_replay_data):
        """Each wave nuke has required fields."""
        nukes = lane_svc.get_wave_nukes(parsed_replay_data)
        for n in nukes[:10]:
            assert n.game_time >= 0
            assert n.game_time_str
            assert n.hero
            assert n.ability
            assert n.creeps_hit >= 2  # Minimum threshold
            assert n.total_damage > 0

    def test_wave_nukes_sorted_by_time(self, lane_svc, parsed_replay_data):
        """Wave nukes are sorted chronologically."""
        nukes = lane_svc.get_wave_nukes(parsed_replay_data)
        times = [n.game_time for n in nukes]
        assert times == sorted(times)


class TestLaneRotations:
    """Tests for get_lane_rotations functionality."""

    def test_returns_list_of_rotations(self, lane_svc, parsed_replay_data):
        """Returns list of LaneRotation models."""
        rotations = lane_svc.get_lane_rotations(parsed_replay_data)
        assert isinstance(rotations, list)
        if rotations:
            assert isinstance(rotations[0], LaneRotation)

    def test_rotation_types_valid(self, lane_svc, parsed_replay_data):
        """Rotation types are valid."""
        rotations = lane_svc.get_lane_rotations(parsed_replay_data)
        valid_types = ["smoke_break", "tp_scroll", "twin_gate"]
        for r in rotations:
            assert r.rotation_type in valid_types

    def test_rotations_sorted_by_time(self, lane_svc, parsed_replay_data):
        """Rotations are sorted chronologically."""
        rotations = lane_svc.get_lane_rotations(parsed_replay_data)
        times = [r.game_time for r in rotations]
        assert times == sorted(times)


class TestHeroPositions:
    """Tests for get_hero_positions_at_minute functionality."""

    def test_returns_list_of_positions(self, lane_svc, parsed_replay_data):
        """Returns list of HeroPosition models."""
        positions = lane_svc.get_hero_positions_at_minute(parsed_replay_data, 5)
        assert isinstance(positions, list)
        assert len(positions) == 10  # All 10 heroes

    def test_positions_have_required_fields(self, lane_svc, parsed_replay_data):
        """Each position has required fields."""
        positions = lane_svc.get_hero_positions_at_minute(parsed_replay_data, 5)
        for pos in positions:
            assert isinstance(pos, HeroPosition)
            assert pos.hero
            assert pos.team in ["radiant", "dire"]
            assert -10000 < pos.x < 10000
            assert -10000 < pos.y < 10000


class TestLaneSummaryResponse:
    """Tests for get_lane_summary functionality with new response model."""

    def test_returns_lane_summary_response(self, lane_svc, parsed_replay_data):
        """Returns LaneSummaryResponse model."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        assert isinstance(summary, LaneSummaryResponse)
        assert summary.success is True

    def test_summary_has_lane_winners(self, lane_svc, parsed_replay_data):
        """Summary includes lane winners."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        assert summary.top_winner in ["radiant", "dire", "even"]
        assert summary.mid_winner in ["radiant", "dire", "even"]
        assert summary.bot_winner in ["radiant", "dire", "even"]

    def test_summary_has_hero_stats(self, lane_svc, parsed_replay_data):
        """Summary includes hero stats."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        assert len(summary.hero_stats) == 10
        for hero in summary.hero_stats:
            assert isinstance(hero, HeroLanePhase)
            assert hero.hero
            assert hero.team in ["radiant", "dire"]

    def test_hero_stats_have_cs_data(self, lane_svc, parsed_replay_data):
        """Hero stats include CS data."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        total_cs = sum(h.last_hits_10min for h in summary.hero_stats)
        assert total_cs > 100  # Total team CS at 10 min

    def test_hero_stats_have_harass_data(self, lane_svc, parsed_replay_data):
        """Hero stats include harass data."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        total_harass = sum(h.damage_dealt_to_heroes for h in summary.hero_stats)
        assert total_harass > 0  # Some harass damage

    def test_hero_stats_have_last_hit_events(self, lane_svc, parsed_replay_data):
        """Hero stats include detailed last hit events."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        total_events = sum(len(h.last_hit_events) for h in summary.hero_stats)
        assert total_events > 0

    def test_hero_stats_have_harass_events(self, lane_svc, parsed_replay_data):
        """Hero stats include detailed harass events."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        total_events = sum(len(h.harass_events) for h in summary.hero_stats)
        assert total_events > 0

    def test_summary_includes_rotations(self, lane_svc, parsed_replay_data):
        """Summary includes rotation events."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        assert isinstance(summary.rotations, list)

    def test_summary_includes_wave_nukes(self, lane_svc, parsed_replay_data):
        """Summary includes wave nuke events."""
        summary = lane_svc.get_lane_summary(parsed_replay_data)
        assert isinstance(summary.wave_nukes, list)


class TestMatch8594217096LaneAnalysis:
    """Tests for lane analysis on match 8594217096 (OG match)."""

    def test_juggernaut_early_cs(self, parsed_replay_data_2):
        """Juggernaut has CS at minute 5."""
        lane_svc = LaneService()
        cs = lane_svc.get_cs_at_minute(parsed_replay_data_2, 5)
        juggernaut_cs = cs.get("juggernaut", {})
        assert juggernaut_cs.get("last_hits", 0) > 15  # Decent CS by 5 min

    def test_pugna_nether_blast_wave_nuke(self, parsed_replay_data_2):
        """Pugna used Nether Blast to push wave."""
        lane_svc = LaneService()
        nukes = lane_svc.get_wave_nukes(parsed_replay_data_2, hero_filter="pugna")
        nether_blasts = [n for n in nukes if "nether_blast" in n.ability.lower()]
        assert len(nether_blasts) > 0  # Pugna used Nether Blast on creeps

    def test_harass_detected_in_early_game(self, parsed_replay_data_2):
        """Harass events detected in first 3 minutes."""
        lane_svc = LaneService()
        harass = lane_svc.get_lane_harass(parsed_replay_data_2, end_time=180)
        assert len(harass) > 0  # Early game trading

    def test_batrider_firefly_harass(self, parsed_replay_data_2):
        """Batrider's Firefly harass detected."""
        lane_svc = LaneService()
        harass = lane_svc.get_lane_harass(parsed_replay_data_2, hero_filter="batrider")
        firefly = [h for h in harass if h.ability and "firefly" in h.ability.lower()]
        assert len(firefly) > 0


# =============================================================================
# Wave Detection Tests (Match 8594217096 - SLAM V Final)
# =============================================================================


class TestWaveDetection:
    """Tests for get_lane_waves wave-by-wave CS tracking."""

    def test_get_lane_waves_returns_creep_wave_list(self, parsed_replay_data_2):
        """get_lane_waves returns list of CreepWave models."""
        from src.services.models.lane_data import CreepWave

        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(w, CreepWave) for w in result)

    def test_waves_sorted_by_wave_number(self, parsed_replay_data_2):
        """Waves are sorted by wave number."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        wave_nums = [w.wave_number for w in result]
        assert wave_nums == sorted(wave_nums)

    def test_wave_spawn_times_30_second_intervals(self, parsed_replay_data_2):
        """Wave spawn times are 0, 30, 60, etc."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        for wave in result:
            expected_spawn = (wave.wave_number - 1) * 30
            assert wave.spawn_time == expected_spawn

    def test_wave_has_last_hits_populated(self, parsed_replay_data_2):
        """Waves have last_hits list with CS events."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        waves_with_cs = [w for w in result if len(w.last_hits) > 0]
        assert len(waves_with_cs) > 0

    def test_wave_death_times_within_35_65_window(self, parsed_replay_data_2):
        """Deaths occur within spawn+35 to spawn+65 window."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        for wave in result:
            if wave.first_death_time:
                assert wave.first_death_time >= wave.spawn_time + 35
                assert wave.first_death_time < wave.spawn_time + 65

    def test_hero_filter_limits_to_single_hero(self, parsed_replay_data_2):
        """Hero filter only includes CS from specified hero."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        for wave in result:
            for lh in wave.last_hits:
                assert lh.hero == "juggernaut"

    def test_last_hit_has_wave_number_set(self, parsed_replay_data_2):
        """Last hits have wave_number matching parent wave."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        for wave in result:
            for lh in wave.last_hits:
                assert lh.wave_number == wave.wave_number

    def test_melee_ranged_counts_accurate(self, parsed_replay_data_2):
        """Melee/ranged death counts are consistent with total_deaths."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        for wave in result:
            # melee_deaths + ranged_deaths should equal total_deaths
            assert wave.melee_deaths + wave.ranged_deaths == wave.total_deaths

    def test_total_deaths_gte_last_hits_count(self, parsed_replay_data_2):
        """total_deaths >= len(last_hits) (some deaths may not be hero CS)."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        for wave in result:
            # Not all deaths are hero last hits - creeps kill creeps too
            assert wave.total_deaths >= len(wave.last_hits)

    def test_no_overlapping_wave_assignments(self, parsed_replay_data_2):
        """Same CS event doesn't appear in multiple waves."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")

        # Track which wave each CS appears in by (time, target, wave_number)
        cs_waves: dict[tuple[float, str], list[int]] = {}
        for wave in result:
            for lh in wave.last_hits:
                key = (lh.game_time, lh.target)
                if key not in cs_waves:
                    cs_waves[key] = []
                cs_waves[key].append(wave.wave_number)

        # Each (time, target) should only appear in ONE wave
        # Note: Two creeps can die at the same time (AoE), which is fine
        # as long as they're in the same wave
        for key, wave_nums in cs_waves.items():
            unique_waves = set(wave_nums)
            assert len(unique_waves) == 1, f"CS at {key} appears in multiple waves: {unique_waves}"


class TestWaveDetectionJuggernautSLAMV:
    """Specific tests for Juggernaut waves in SLAM V Final (match 8594217096)."""

    def test_juggernaut_wave_1_has_cs(self, parsed_replay_data_2):
        """Juggernaut gets CS on wave 1."""
        lane_svc = LaneService()
        waves = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        wave_1 = next((w for w in waves if w.wave_number == 1), None)
        assert wave_1 is not None
        assert len(wave_1.last_hits) >= 3  # Pure got 4 LH on wave 1

    def test_juggernaut_first_5_waves_have_cs(self, parsed_replay_data_2):
        """Juggernaut gets CS on first 5 waves."""
        lane_svc = LaneService()
        waves = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut",
            end_time=180
        )

        # Should have waves 1-5 with CS
        wave_numbers = [w.wave_number for w in waves]
        assert 1 in wave_numbers
        assert 2 in wave_numbers or 3 in wave_numbers  # At least a couple early waves

    def test_wave_1_first_death_around_42_seconds(self, parsed_replay_data_2):
        """Wave 1 first death around 0:42 (verified from replay)."""
        lane_svc = LaneService()
        waves = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        wave_1 = next((w for w in waves if w.wave_number == 1), None)
        if wave_1 and wave_1.first_death_time:
            # First death should be around 40-45 seconds
            assert 38 <= wave_1.first_death_time <= 50

    def test_wave_number_calculation_consistency(self, parsed_replay_data_2):
        """Wave number calculation is consistent across calls."""
        lane_svc = LaneService()

        # Call twice with same params
        waves1 = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        waves2 = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )

        # Should get same results
        assert len(waves1) == len(waves2)
        for w1, w2 in zip(waves1, waves2):
            assert w1.wave_number == w2.wave_number
            assert len(w1.last_hits) == len(w2.last_hits)


# =============================================================================
# Entity-Based Wave Detection Tests (requires python-manta 1.4.5.4+)
# =============================================================================


class TestEntityBasedWaveDetection:
    """Tests for get_lane_waves with entity_deaths correlation."""

    def test_get_lane_waves_returns_creep_wave_list(self, parsed_replay_data_2):
        """get_lane_waves returns list of CreepWave with entity_deaths data."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        assert isinstance(result, list)
        assert len(result) > 0  # Must have waves

    def test_get_lane_waves_uses_entity_deaths(self, parsed_replay_data_2):
        """get_lane_waves uses entity_deaths collector data."""
        # Verify entity_deaths data exists
        assert parsed_replay_data_2.entity_deaths is not None
        assert len(parsed_replay_data_2.entity_deaths.events) > 0

    def test_get_lane_waves_uses_attacks(self, parsed_replay_data_2):
        """get_lane_waves uses attacks collector data."""
        # Verify attacks data exists
        assert parsed_replay_data_2.attacks is not None
        assert len(parsed_replay_data_2.attacks.events) > 0

    def test_waves_sorted_by_wave_number(self, parsed_replay_data_2):
        """Waves are sorted by wave_number."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(parsed_replay_data_2, lane="bot", team="dire")
        wave_nums = [w.wave_number for w in result]
        assert wave_nums == sorted(wave_nums)

    def test_hero_filter_works(self, parsed_replay_data_2):
        """Can filter by hero."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        # All last_hits should be from juggernaut
        for wave in result:
            for lh in wave.last_hits:
                assert "juggernaut" in lh.hero.lower()

    def test_wave_has_entity_correlated_cs(self, parsed_replay_data_2):
        """Waves have CS determined via attack correlation."""
        lane_svc = LaneService()
        result = lane_svc.get_lane_waves(
            parsed_replay_data_2, lane="bot", team="dire", hero_filter="juggernaut"
        )
        # Should have multiple waves with CS
        waves_with_cs = [w for w in result if len(w.last_hits) > 0]
        assert len(waves_with_cs) >= 5  # Juggernaut gets CS on many waves


class TestContestedCS:
    """Tests for get_contested_cs detection."""

    def test_contested_cs_returns_list(self, parsed_replay_data_2):
        """get_contested_cs returns list of dicts."""
        lane_svc = LaneService()
        result = lane_svc.get_contested_cs(parsed_replay_data_2, lane="bot", team="dire")
        assert isinstance(result, list)

    def test_contested_cs_has_required_fields(self, parsed_replay_data_2):
        """Contested CS events have expected fields."""
        lane_svc = LaneService()
        result = lane_svc.get_contested_cs(parsed_replay_data_2, lane="bot", team="dire")

        for cs in result[:5]:
            assert 'game_time' in cs
            assert 'game_time_str' in cs
            assert 'entity_id' in cs
            assert 'creep_name' in cs
            assert 'wave_number' in cs
            assert 'hero_attackers' in cs
            assert 'last_hitter' in cs
            assert len(cs['hero_attackers']) >= 2  # Must have 2+ attackers to be contested

    def test_contested_cs_sorted_by_time(self, parsed_replay_data_2):
        """Contested CS events are sorted by time."""
        lane_svc = LaneService()
        result = lane_svc.get_contested_cs(parsed_replay_data_2, lane="bot", team="dire")

        if result:
            times = [cs['game_time'] for cs in result]
            assert times == sorted(times)


class TestAttackIndex:
    """Tests for _build_attack_index helper."""

    def test_attack_index_returns_dict(self, parsed_replay_data_2):
        """_build_attack_index returns dict with attack data."""
        lane_svc = LaneService()
        result = lane_svc._build_attack_index(parsed_replay_data_2)
        assert isinstance(result, dict)
        assert len(result) > 0  # Must have attack data

    def test_attack_index_has_entity_ids(self, parsed_replay_data_2):
        """Attack index maps entity_id to attacks."""
        lane_svc = LaneService()
        result = lane_svc._build_attack_index(parsed_replay_data_2)

        # Keys should be entity IDs (integers)
        for entity_id in list(result.keys())[:5]:
            assert isinstance(entity_id, int)
            attacks = result[entity_id]
            assert isinstance(attacks, list)
            assert len(attacks) > 0


# =============================================================================
# Neutral Aggro Tests (Match 8461956309)
# =============================================================================


class TestNeutralAggroInLaneSummary:
    """Tests for neutral aggro tracking in lane summary."""

    def test_lane_summary_has_neutral_aggro_list(self, lane_summary):
        """Lane summary should include neutral_aggro list."""
        assert hasattr(lane_summary, 'neutral_aggro')
        assert isinstance(lane_summary.neutral_aggro, list)

    def test_neutral_aggro_count(self, lane_summary):
        """Should detect significant number of neutral aggro events."""
        assert len(lane_summary.neutral_aggro) >= 800

    def test_neutral_aggro_fields(self, lane_summary):
        """Neutral aggro events should have required fields."""
        from src.services.models.lane_data import NeutralAggro

        if lane_summary.neutral_aggro:
            na = lane_summary.neutral_aggro[0]
            assert isinstance(na, NeutralAggro)
            assert hasattr(na, 'game_time')
            assert hasattr(na, 'game_time_str')
            assert hasattr(na, 'hero')
            assert hasattr(na, 'target')
            assert hasattr(na, 'damage')
            assert hasattr(na, 'camp_type')
            assert hasattr(na, 'near_lane')

    def test_nevermore_has_most_neutral_aggro(self, lane_summary):
        """Nevermore (SF mid) should have most neutral aggro in laning phase."""
        by_hero = {}
        for na in lane_summary.neutral_aggro:
            if na.hero not in by_hero:
                by_hero[na.hero] = 0
            by_hero[na.hero] += 1

        most_aggro_hero = max(by_hero.keys(), key=lambda h: by_hero[h])
        assert most_aggro_hero == "nevermore"
        assert by_hero["nevermore"] >= 150

    def test_first_neutral_aggro_is_naga(self, lane_summary):
        """First neutral aggro should be Naga Siren at 2:20."""
        sorted_aggro = sorted(lane_summary.neutral_aggro, key=lambda x: x.game_time)
        first = sorted_aggro[0]
        assert first.hero == "naga_siren"
        assert first.game_time_str == "2:20"

    def test_neutral_aggro_targets_are_neutrals(self, lane_summary):
        """All neutral aggro targets should be neutral creeps."""
        for na in lane_summary.neutral_aggro:
            assert "neutral" in na.target.lower()

    def test_hero_stats_have_neutral_aggro_counts(self, lane_summary):
        """Each hero's lane stats should have neutral_attacks count."""
        for hs in lane_summary.hero_stats:
            assert hasattr(hs, 'neutral_attacks')
            assert hasattr(hs, 'pull_attempts')
            assert isinstance(hs.neutral_attacks, int)


class TestNeutralAggroMethod:
    """Tests for get_neutral_aggro service method."""

    def test_get_neutral_aggro_returns_list(self, parsed_replay_data):
        """get_neutral_aggro should return list of NeutralAggro."""
        from src.services.models.lane_data import NeutralAggro

        svc = LaneService()
        result = svc.get_neutral_aggro(parsed_replay_data)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(na, NeutralAggro) for na in result)

    def test_get_neutral_aggro_filter_by_hero(self, parsed_replay_data):
        """get_neutral_aggro should filter by hero."""
        svc = LaneService()
        result = svc.get_neutral_aggro(parsed_replay_data, hero_filter="nevermore")
        assert all(na.hero == "nevermore" for na in result)

    def test_get_neutral_aggro_sorted_by_time(self, parsed_replay_data):
        """get_neutral_aggro results should be sorted by time."""
        svc = LaneService()
        result = svc.get_neutral_aggro(parsed_replay_data)
        times = [na.game_time for na in result]
        assert times == sorted(times)


# =============================================================================
# Tower Pressure Tests (Match 8461956309)
# =============================================================================


class TestTowerPressureInLaneSummary:
    """Tests for tower pressure tracking in lane summary."""

    def test_lane_summary_has_tower_pressure_list(self, lane_summary):
        """Lane summary should include tower_pressure list."""
        assert hasattr(lane_summary, 'tower_pressure')
        assert isinstance(lane_summary.tower_pressure, list)

    def test_tower_pressure_count(self, lane_summary):
        """Should detect tower pressure events."""
        assert len(lane_summary.tower_pressure) >= 20

    def test_tower_pressure_fields(self, lane_summary):
        """Tower pressure events should have required fields."""
        from src.services.models.lane_data import TowerPressure

        if lane_summary.tower_pressure:
            tp = lane_summary.tower_pressure[0]
            assert isinstance(tp, TowerPressure)
            assert hasattr(tp, 'game_time')
            assert hasattr(tp, 'game_time_str')
            assert hasattr(tp, 'tower')
            assert hasattr(tp, 'hero')
            assert hasattr(tp, 'damage')
            assert hasattr(tp, 'tower_team')
            assert hasattr(tp, 'lane')

    def test_naga_siren_takes_most_tower_damage(self, lane_summary):
        """Naga Siren should take most tower damage in laning phase."""
        by_hero = {}
        for tp in lane_summary.tower_pressure:
            if tp.hero not in by_hero:
                by_hero[tp.hero] = {"hits": 0, "damage": 0}
            by_hero[tp.hero]["hits"] += 1
            by_hero[tp.hero]["damage"] += tp.damage

        most_damage_hero = max(by_hero.keys(), key=lambda h: by_hero[h]["damage"])
        assert most_damage_hero == "naga_siren"
        assert by_hero["naga_siren"]["damage"] >= 3000
        assert by_hero["naga_siren"]["hits"] >= 10

    def test_tower_names_are_valid(self, lane_summary):
        """Tower names should follow standard naming pattern."""
        for tp in lane_summary.tower_pressure:
            assert "tower" in tp.tower.lower()
            assert "goodguys" in tp.tower.lower() or "badguys" in tp.tower.lower()

    def test_tower_team_matches_tower_name(self, lane_summary):
        """Tower team should match the tower name."""
        for tp in lane_summary.tower_pressure:
            if "goodguys" in tp.tower.lower():
                assert tp.tower_team == "radiant"
            elif "badguys" in tp.tower.lower():
                assert tp.tower_team == "dire"

    def test_hero_stats_have_tower_pressure_counts(self, lane_summary):
        """Each hero's lane stats should have tower pressure counts."""
        for hs in lane_summary.hero_stats:
            assert hasattr(hs, 'tower_damage_taken')
            assert hasattr(hs, 'tower_hits_received')
            assert isinstance(hs.tower_damage_taken, int)
            assert isinstance(hs.tower_hits_received, int)


class TestTowerPressureMethod:
    """Tests for get_tower_pressure service method."""

    def test_get_tower_pressure_returns_list(self, parsed_replay_data):
        """get_tower_pressure should return list of TowerPressure."""
        from src.services.models.lane_data import TowerPressure

        svc = LaneService()
        result = svc.get_tower_pressure(parsed_replay_data)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(tp, TowerPressure) for tp in result)

    def test_get_tower_pressure_filter_by_hero(self, parsed_replay_data):
        """get_tower_pressure should filter by hero."""
        svc = LaneService()
        result = svc.get_tower_pressure(parsed_replay_data, hero_filter="naga_siren")
        assert all(tp.hero == "naga_siren" for tp in result)

    def test_get_tower_pressure_sorted_by_time(self, parsed_replay_data):
        """get_tower_pressure results should be sorted by time."""
        svc = LaneService()
        result = svc.get_tower_pressure(parsed_replay_data)
        times = [tp.game_time for tp in result]
        assert times == sorted(times)
