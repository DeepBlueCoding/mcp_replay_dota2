"""
Tests for combat log parser.

Uses pre-parsed replay data from conftest.py fixtures.
All data is from match 8461956309 with verified values from Dotabuff.
"""

import pytest

from src.models.combat_log import (
    BarracksKill,
    CombatLogEvent,
    FightResult,
    HeroDeath,
    MapLocation,
    RoshanKill,
    RunePickup,
    TormentorKill,
    TowerKill,
)

# Verified data from Dotabuff for match 8461956309
FIRST_BLOOD_TIME = 288.0
FIRST_BLOOD_VICTIM = "earthshaker"
FIRST_BLOOD_KILLER = "disruptor"
FIRST_BLOOD_ABILITY = "disruptor_thunder_strike"


class TestCombatLogParser:

    def test_get_hero_deaths_returns_list_of_hero_death_models(self, hero_deaths):
        assert len(hero_deaths) > 0
        assert all(isinstance(d, HeroDeath) for d in hero_deaths)

    def test_get_hero_deaths_first_blood_matches_dotabuff(self, hero_deaths):
        first_death = hero_deaths[0]
        assert first_death.victim == FIRST_BLOOD_VICTIM
        assert first_death.killer == FIRST_BLOOD_KILLER
        assert first_death.ability == FIRST_BLOOD_ABILITY
        assert abs(first_death.game_time - FIRST_BLOOD_TIME) < 2.0

    def test_get_hero_deaths_has_correct_time_format(self, hero_deaths):
        first_death = hero_deaths[0]
        assert first_death.game_time_str == "4:48"

    def test_get_combat_log_returns_combat_log_event_models(self, combat_log_280_290):
        assert len(combat_log_280_290) > 0
        assert all(isinstance(e, CombatLogEvent) for e in combat_log_280_290)

    def test_get_combat_log_filters_by_time(self, combat_log_280_290):
        for event in combat_log_280_290:
            assert 280 <= event.game_time <= 290

    def test_get_combat_log_filters_by_hero(self, combat_log_280_290_earthshaker):
        for event in combat_log_280_290_earthshaker:
            assert "earthshaker" in event.attacker.lower() or "earthshaker" in event.target.lower()

    def test_get_combat_log_includes_death_event(self, combat_log_287_289_earthshaker):
        death_events = [e for e in combat_log_287_289_earthshaker if e.type == "DEATH"]
        assert len(death_events) >= 1

        es_death = [e for e in death_events if e.target == "earthshaker"]
        assert len(es_death) == 1
        assert es_death[0].attacker == "disruptor"


class TestFightDetection:

    def test_get_combat_timespan_returns_fight_result_model(self, fight_first_blood):
        assert isinstance(fight_first_blood, FightResult)

    def test_first_blood_fight_has_correct_participants(self, fight_first_blood):
        assert "earthshaker" in fight_first_blood.participants
        assert "disruptor" in fight_first_blood.participants
        assert "naga_siren" in fight_first_blood.participants
        assert "medusa" in fight_first_blood.participants

    def test_first_blood_fight_duration_reasonable(self, fight_first_blood):
        assert 5 <= fight_first_blood.duration <= 20

    def test_fight_detection_separates_concurrent_fights(self, fight_first_blood, fight_pango_nevermore):
        assert "pangolier" not in fight_first_blood.participants
        assert "nevermore" not in fight_first_blood.participants
        assert "earthshaker" not in fight_pango_nevermore.participants

    def test_pango_nevermore_fight_isolated(self, fight_pango_nevermore):
        assert set(fight_pango_nevermore.participants) == {"nevermore", "pangolier"}
        assert fight_pango_nevermore.duration < 5

    def test_fight_events_are_combat_log_event_models(self, fight_first_blood):
        assert all(isinstance(e, CombatLogEvent) for e in fight_first_blood.events)

    def test_fight_without_hero_anchor_finds_nearest_fight(self, fight_first_blood_no_hero):
        assert "earthshaker" in fight_first_blood_no_hero.participants
        assert fight_first_blood_no_hero.total_events > 0


class TestObjectiveKills:

    def test_get_objective_kills_returns_correct_tuple_structure(self, objectives):
        assert isinstance(objectives, tuple)
        assert len(objectives) == 4
        roshan, tormentor, towers, barracks = objectives
        assert isinstance(roshan, list)
        assert isinstance(tormentor, list)
        assert isinstance(towers, list)
        assert isinstance(barracks, list)

    def test_roshan_kills_correct_count_and_order(self, objectives):
        roshan, _, _, _ = objectives
        assert len(roshan) == 4
        assert all(isinstance(r, RoshanKill) for r in roshan)
        for i, r in enumerate(roshan):
            assert r.kill_number == i + 1

    def test_first_roshan_kill_details(self, objectives):
        roshan, _, _, _ = objectives
        first_rosh = roshan[0]
        assert first_rosh.game_time_str == "23:12"
        assert first_rosh.killer == "medusa"
        assert first_rosh.team == "dire"
        assert first_rosh.kill_number == 1

    def test_tormentor_kills_correct_count(self, objectives):
        _, tormentor, _, _ = objectives
        assert len(tormentor) == 4
        assert all(isinstance(t, TormentorKill) for t in tormentor)

    def test_first_tormentor_kill_details(self, objectives):
        _, tormentor, _, _ = objectives
        first_tormentor = tormentor[0]
        assert first_tormentor.game_time_str == "20:15"
        assert first_tormentor.killer == "medusa"
        assert first_tormentor.team == "dire"

    def test_tower_kills_correct_count(self, objectives):
        _, _, towers, _ = objectives
        assert len(towers) == 14
        assert all(isinstance(t, TowerKill) for t in towers)

    def test_first_tower_kill_details(self, objectives):
        _, _, towers, _ = objectives
        first_tower = towers[0]
        assert first_tower.game_time_str == "11:09"
        assert first_tower.tower == "dire_t1_mid"
        assert first_tower.team == "dire"
        assert first_tower.tier == 1
        assert first_tower.lane == "mid"
        assert first_tower.killer == "nevermore"
        assert first_tower.killer_is_hero is True

    def test_barracks_kills_correct_count(self, objectives):
        _, _, _, barracks = objectives
        assert len(barracks) == 6
        assert all(isinstance(b, BarracksKill) for b in barracks)

    def test_first_barracks_kill_details(self, objectives):
        _, _, _, barracks = objectives
        first_rax = barracks[0]
        assert first_rax.game_time_str == "39:33"
        assert first_rax.barracks == "radiant_melee_mid"
        assert first_rax.team == "radiant"
        assert first_rax.lane == "mid"
        assert first_rax.type == "melee"
        assert first_rax.killer == "medusa"

    def test_all_barracks_are_radiant(self, objectives):
        _, _, _, barracks = objectives
        for rax in barracks:
            assert rax.team == "radiant"


class TestPositionTracking:

    def test_hero_deaths_include_position(self, hero_deaths_with_position):
        deaths_with_pos = [d for d in hero_deaths_with_position if d.position is not None]
        assert len(deaths_with_pos) > 0

    def test_hero_death_position_has_correct_structure(self, hero_deaths_with_position):
        death_with_pos = next((d for d in hero_deaths_with_position if d.position is not None), None)
        assert death_with_pos is not None

        pos = death_with_pos.position
        assert isinstance(pos, MapLocation)
        assert isinstance(pos.x, float)
        assert isinstance(pos.y, float)
        assert isinstance(pos.region, str)
        assert isinstance(pos.location, str)

    def test_first_blood_death_position_is_dire_safelane(self, hero_deaths_with_position):
        first_death = hero_deaths_with_position[0]
        assert first_death.victim == "earthshaker"
        assert first_death.position is not None
        assert "dire" in first_death.position.region.lower() or "dire" in first_death.position.location.lower()

    def test_hero_deaths_without_position_flag(self, hero_deaths):
        for death in hero_deaths:
            assert death.position is None

    def test_position_coordinates_in_valid_range(self, hero_deaths_with_position):
        for death in hero_deaths_with_position:
            if death.position:
                assert -8500 <= death.position.x <= 8500
                assert -8500 <= death.position.y <= 8500


class TestRunePickups:

    def test_get_rune_pickups_returns_list_of_rune_pickup_models(self, rune_pickups):
        assert len(rune_pickups) > 0
        assert all(isinstance(p, RunePickup) for p in rune_pickups)

    def test_rune_pickups_correct_count(self, rune_pickups):
        assert len(rune_pickups) == 19

    def test_first_rune_pickup_details(self, rune_pickups):
        first_rune = rune_pickups[0]
        assert first_rune.game_time_str == "6:14"
        assert first_rune.hero == "naga_siren"
        assert first_rune.rune_type == "Arcane"

    def test_rune_pickups_sorted_by_time(self, rune_pickups):
        times = [p.game_time for p in rune_pickups]
        assert times == sorted(times)

    def test_rune_types_are_valid(self, rune_pickups):
        from python_manta import RuneType
        valid_types = {r.display_name for r in RuneType}
        for pickup in rune_pickups:
            assert pickup.rune_type in valid_types

    def test_pangolier_most_rune_pickups(self, rune_pickups):
        hero_counts = {}
        for p in rune_pickups:
            hero_counts[p.hero] = hero_counts.get(p.hero, 0) + 1

        assert max(hero_counts, key=hero_counts.get) == "pangolier"
        assert hero_counts["pangolier"] == 9


class TestAbilityHitDetection:

    def test_ability_events_have_hit_field(self, combat_log_280_300_ability):
        ability_events = [e for e in combat_log_280_300_ability if e.type == "ABILITY"]
        assert len(ability_events) > 0
        for e in ability_events:
            assert e.hit in (True, False, None)

    def test_self_buff_abilities_have_hit_none(self, combat_log_280_300_earthshaker_ability):
        totem_events = [e for e in combat_log_280_300_earthshaker_ability if e.ability == "earthshaker_enchant_totem"]
        assert len(totem_events) > 0
        for e in totem_events:
            assert e.hit is None

    def test_ensnare_that_hit_shows_as_true(self, combat_log_280_282_naga_ability):
        ensnare_events = [e for e in combat_log_280_282_naga_ability if e.ability == "naga_siren_ensnare"]
        assert len(ensnare_events) == 1
        assert ensnare_events[0].hit is True

    def test_modifier_prefix_normalization(self):
        from src.utils.combat_log_parser import CombatLogParser
        parser = CombatLogParser()
        assert parser._normalize_ability_name("naga_siren_ensnare") == "naga_siren_ensnare"
        assert parser._normalize_ability_name("modifier_naga_siren_ensnare") == "naga_siren_ensnare"
        assert parser._normalize_ability_name("modifier_rune_haste") == "rune_haste"

    def test_non_ability_events_have_hit_none(self, combat_log_280_290_non_ability):
        for e in combat_log_280_290_non_ability:
            assert e.hit is None

    def test_hit_detection_stats_reasonable(self, combat_log_0_600_ability):
        hits = [e for e in combat_log_0_600_ability if e.hit is True]
        misses = [e for e in combat_log_0_600_ability if e.hit is False]
        na = [e for e in combat_log_0_600_ability if e.hit is None]

        assert len(hits) > 50
        assert len(misses) > 20
        assert len(na) > 100
        assert len(hits) + len(misses) + len(na) == len(combat_log_0_600_ability)


class TestAbilityTrigger:

    def test_ability_trigger_type_in_combatlog_types(self):
        from src.utils.combat_log_parser import CombatLogParser
        parser = CombatLogParser()
        assert 13 in parser.COMBATLOG_TYPES
        assert parser.COMBATLOG_TYPES[13] == "ABILITY_TRIGGER"

    def test_ability_trigger_events_included_by_default(self, combat_log_320_370):
        trigger_events = [e for e in combat_log_320_370 if e.type == "ABILITY_TRIGGER"]
        assert len(trigger_events) > 0

    def test_lotus_orb_reflections_tracked(self, combat_log_trigger_only):
        lotus_events = [e for e in combat_log_trigger_only if e.ability and "lotus" in e.ability.lower()]
        assert len(lotus_events) == 2

    def test_lotus_orb_reflection_structure(self, combat_log_trigger_only):
        lotus_events = [e for e in combat_log_trigger_only if e.ability and "lotus" in e.ability.lower()]
        assert len(lotus_events) > 0

        first = lotus_events[0]
        assert first.attacker == "naga_siren"
        assert first.target == "shadow_demon"
        assert first.ability == "item_lotus_orb"

    def test_ability_trigger_in_fight_detection(self, combat_log_360_370):
        trigger_in_range = [e for e in combat_log_360_370 if e.type == "ABILITY_TRIGGER"]
        assert len(trigger_in_range) > 0
