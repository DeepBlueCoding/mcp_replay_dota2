"""
Tests for combat log parser.

Uses real replay data from match 8461956309 with verified values from Dotabuff.
"""

from pathlib import Path

import pytest

from src.models.combat_log import (
    BarracksKill,
    CombatLogEvent,
    FightResult,
    HeroDeath,
    MapLocation,
    RoshanKill,
    TormentorKill,
    TowerKill,
)
from src.utils.combat_log_parser import CombatLogParser

REAL_MATCH_ID = 8461956309
REPLAY_PATH = Path.home() / "dota2" / "replays" / f"{REAL_MATCH_ID}.dem"

# Verified data from Dotabuff for match 8461956309
# First blood: 04:48 - Earthshaker killed by Disruptor (Thunder Strike)
FIRST_BLOOD_TIME = 288.0  # 4:48 in seconds
FIRST_BLOOD_VICTIM = "earthshaker"
FIRST_BLOOD_KILLER = "disruptor"
FIRST_BLOOD_ABILITY = "disruptor_thunder_strike"


class TestCombatLogParser:

    @pytest.fixture
    def parser(self):
        return CombatLogParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_hero_deaths_returns_list_of_hero_death_models(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH)

        assert len(deaths) > 0
        assert all(isinstance(d, HeroDeath) for d in deaths)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_hero_deaths_first_blood_matches_dotabuff(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH)

        first_death = deaths[0]
        assert first_death.victim == FIRST_BLOOD_VICTIM
        assert first_death.killer == FIRST_BLOOD_KILLER
        assert first_death.ability == FIRST_BLOOD_ABILITY
        assert abs(first_death.game_time - FIRST_BLOOD_TIME) < 2.0  # Within 2 seconds

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_hero_deaths_has_correct_time_format(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH)

        first_death = deaths[0]
        assert first_death.game_time_str == "4:48"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_combat_log_returns_combat_log_event_models(self, parser):
        events = parser.get_combat_log(
            REPLAY_PATH,
            start_time=280,
            end_time=290,
        )

        assert len(events) > 0
        assert all(isinstance(e, CombatLogEvent) for e in events)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_combat_log_filters_by_time(self, parser):
        events = parser.get_combat_log(
            REPLAY_PATH,
            start_time=280,
            end_time=290,
        )

        for event in events:
            assert 280 <= event.game_time <= 290

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_combat_log_filters_by_hero(self, parser):
        events = parser.get_combat_log(
            REPLAY_PATH,
            start_time=280,
            end_time=290,
            hero_filter="earthshaker",
        )

        for event in events:
            assert "earthshaker" in event.attacker.lower() or "earthshaker" in event.target.lower()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_combat_log_includes_death_event(self, parser):
        events = parser.get_combat_log(
            REPLAY_PATH,
            start_time=287,
            end_time=289,
            hero_filter="earthshaker",
        )

        death_events = [e for e in events if e.type == "DEATH"]
        assert len(death_events) >= 1

        es_death = [e for e in death_events if e.target == "earthshaker"]
        assert len(es_death) == 1
        assert es_death[0].attacker == "disruptor"


class TestFightDetection:

    @pytest.fixture
    def parser(self):
        return CombatLogParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_combat_timespan_returns_fight_result_model(self, parser):
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero="earthshaker",
        )

        assert isinstance(result, FightResult)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_blood_fight_has_correct_participants(self, parser):
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero="earthshaker",
        )

        # Verified participants in first blood fight
        assert "earthshaker" in result.participants
        assert "disruptor" in result.participants
        assert "naga_siren" in result.participants
        assert "medusa" in result.participants

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_blood_fight_duration_reasonable(self, parser):
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero="earthshaker",
        )

        # Fight should be between 5-20 seconds for a first blood
        assert 5 <= result.duration <= 20

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_fight_detection_separates_concurrent_fights(self, parser):
        # At ~4:27, there's a separate Pangolier vs Nevermore fight in mid
        # This should NOT be included in the earthshaker first blood fight

        es_fight = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero="earthshaker",
        )

        pango_fight = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=268,  # 4:28
            hero="pangolier",
        )

        # These should be separate fights with different participants
        assert "pangolier" not in es_fight.participants
        assert "nevermore" not in es_fight.participants
        assert "earthshaker" not in pango_fight.participants

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_pango_nevermore_fight_isolated(self, parser):
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=268,
            hero="pangolier",
        )

        # Should only have pangolier and nevermore
        assert set(result.participants) == {"nevermore", "pangolier"}
        assert result.duration < 5  # Short skirmish

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_fight_events_are_combat_log_event_models(self, parser):
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero="earthshaker",
        )

        assert all(isinstance(e, CombatLogEvent) for e in result.events)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_fight_without_hero_anchor_finds_nearest_fight(self, parser):
        # Without hero anchor, should find the fight closest to reference time
        result = parser.get_combat_timespan(
            REPLAY_PATH,
            reference_time=FIRST_BLOOD_TIME,
            hero=None,
        )

        # Should still find the ES first blood fight since it's at the reference time
        assert "earthshaker" in result.participants
        assert result.total_events > 0


class TestObjectiveKills:
    """Tests for Roshan, Tormentor, tower, and barracks kill tracking."""

    @pytest.fixture
    def parser(self):
        return CombatLogParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_get_objective_kills_returns_correct_tuple_structure(self, parser):
        result = parser.get_objective_kills(REPLAY_PATH)

        assert isinstance(result, tuple)
        assert len(result) == 4
        roshan, tormentor, towers, barracks = result
        assert isinstance(roshan, list)
        assert isinstance(tormentor, list)
        assert isinstance(towers, list)
        assert isinstance(barracks, list)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_roshan_kills_correct_count_and_order(self, parser):
        roshan, _, _, _ = parser.get_objective_kills(REPLAY_PATH)

        # Match 8461956309 has 4 Roshan kills
        assert len(roshan) == 4
        assert all(isinstance(r, RoshanKill) for r in roshan)

        # Verify kill numbers are sequential
        for i, r in enumerate(roshan):
            assert r.kill_number == i + 1

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_roshan_kill_details(self, parser):
        roshan, _, _, _ = parser.get_objective_kills(REPLAY_PATH)

        first_rosh = roshan[0]
        assert first_rosh.game_time_str == "23:12"
        assert first_rosh.killer == "medusa"
        assert first_rosh.team == "dire"
        assert first_rosh.kill_number == 1

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_tormentor_kills_correct_count(self, parser):
        _, tormentor, _, _ = parser.get_objective_kills(REPLAY_PATH)

        # Match 8461956309 has 4 Tormentor kills
        assert len(tormentor) == 4
        assert all(isinstance(t, TormentorKill) for t in tormentor)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_tormentor_kill_details(self, parser):
        _, tormentor, _, _ = parser.get_objective_kills(REPLAY_PATH)

        first_tormentor = tormentor[0]
        assert first_tormentor.game_time_str == "20:15"
        assert first_tormentor.killer == "medusa"
        assert first_tormentor.team == "dire"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_tower_kills_correct_count(self, parser):
        _, _, towers, _ = parser.get_objective_kills(REPLAY_PATH)

        # Match 8461956309 has 14 tower kills
        assert len(towers) == 14
        assert all(isinstance(t, TowerKill) for t in towers)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_tower_kill_details(self, parser):
        _, _, towers, _ = parser.get_objective_kills(REPLAY_PATH)

        first_tower = towers[0]
        assert first_tower.game_time_str == "11:09"
        assert first_tower.tower == "dire_t1_mid"
        assert first_tower.team == "dire"
        assert first_tower.tier == 1
        assert first_tower.lane == "mid"
        assert first_tower.killer == "nevermore"
        assert first_tower.killer_is_hero is True

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_barracks_kills_correct_count(self, parser):
        _, _, _, barracks = parser.get_objective_kills(REPLAY_PATH)

        # Match 8461956309 has 6 barracks kills (all radiant rax destroyed = mega creeps)
        assert len(barracks) == 6
        assert all(isinstance(b, BarracksKill) for b in barracks)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_barracks_kill_details(self, parser):
        _, _, _, barracks = parser.get_objective_kills(REPLAY_PATH)

        first_rax = barracks[0]
        assert first_rax.game_time_str == "39:33"
        assert first_rax.barracks == "radiant_melee_mid"
        assert first_rax.team == "radiant"
        assert first_rax.lane == "mid"
        assert first_rax.type == "melee"
        assert first_rax.killer == "medusa"

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_all_barracks_are_radiant(self, parser):
        _, _, _, barracks = parser.get_objective_kills(REPLAY_PATH)

        # Dire won - all destroyed barracks should be Radiant
        for rax in barracks:
            assert rax.team == "radiant"


class TestPositionTracking:
    """Tests for position tracking in hero deaths and courier kills."""

    @pytest.fixture
    def parser(self):
        return CombatLogParser()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_hero_deaths_include_position(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH, include_position=True)

        # At least some deaths should have position data
        deaths_with_position = [d for d in deaths if d.position is not None]
        assert len(deaths_with_position) > 0

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_hero_death_position_has_correct_structure(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH, include_position=True)

        death_with_pos = next((d for d in deaths if d.position is not None), None)
        assert death_with_pos is not None

        pos = death_with_pos.position
        assert isinstance(pos, MapLocation)
        assert isinstance(pos.x, float)
        assert isinstance(pos.y, float)
        assert isinstance(pos.region, str)
        assert isinstance(pos.location, str)

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_first_blood_death_position_is_dire_safelane(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH, include_position=True)

        # First death (Earthshaker) should be in dire safelane area
        first_death = deaths[0]
        assert first_death.victim == "earthshaker"
        assert first_death.position is not None
        assert "dire" in first_death.position.region.lower() or "dire" in first_death.position.location.lower()

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_hero_deaths_without_position_flag(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH, include_position=False)

        # All deaths should have position=None when flag is False
        for death in deaths:
            assert death.position is None

    @pytest.mark.skipif(not REPLAY_PATH.exists(), reason="Replay file not available")
    def test_position_coordinates_in_valid_range(self, parser):
        deaths = parser.get_hero_deaths(REPLAY_PATH, include_position=True)

        for death in deaths:
            if death.position:
                # Map coordinates should be within valid range (-8000 to 8000)
                assert -8500 <= death.position.x <= 8500
                assert -8500 <= death.position.y <= 8500
