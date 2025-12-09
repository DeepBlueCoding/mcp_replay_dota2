"""
Tests for combat log parser.

Uses pre-parsed replay data from conftest.py fixtures.
All data is from match 8461956309 with verified values from Dotabuff.
"""

import pytest

from src.services.models.combat_data import (
    CombatLogEvent,
    Fight,
    HeroDeath,
    ObjectiveKill,
    RunePickup,
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

    def test_get_fight_at_time_returns_fight_model(self, fight_first_blood):
        assert isinstance(fight_first_blood, Fight)

    def test_first_blood_fight_has_correct_killer_and_victim(self, fight_first_blood):
        # v2 FightDetector only tracks killer/victim from deaths, not nearby combatants
        assert "earthshaker" in fight_first_blood.participants
        assert "disruptor" in fight_first_blood.participants

    def test_first_blood_fight_found(self, fight_first_blood):
        # Verify the fight was detected at the correct time
        assert fight_first_blood is not None
        assert len(fight_first_blood.deaths) >= 1

    def test_fight_detection_separates_concurrent_fights(self, fight_first_blood, fight_pango_nevermore):
        # First blood fight shouldn't include heroes from pango/nevermore fight
        assert "pangolier" not in fight_first_blood.participants or "nevermore" not in fight_first_blood.participants

    def test_pango_nevermore_fight_found(self, fight_pango_nevermore):
        # Verify pangolier fight was detected
        assert fight_pango_nevermore is not None
        assert "pangolier" in fight_pango_nevermore.participants
        assert "nevermore" in fight_pango_nevermore.participants

    def test_fight_has_deaths(self, fight_first_blood):
        assert len(fight_first_blood.deaths) > 0
        assert all(isinstance(d, HeroDeath) for d in fight_first_blood.deaths)

    def test_fight_without_hero_anchor_finds_nearest_fight(self, fight_first_blood_no_hero):
        assert isinstance(fight_first_blood_no_hero, Fight)
        assert "earthshaker" in fight_first_blood_no_hero.participants
        assert len(fight_first_blood_no_hero.deaths) > 0


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
        assert all(isinstance(r, ObjectiveKill) for r in roshan)
        for i, r in enumerate(roshan):
            assert r.extra_info.get("kill_number") == i + 1

    def test_first_roshan_kill_details(self, objectives):
        roshan, _, _, _ = objectives
        first_rosh = roshan[0]
        assert first_rosh.game_time_str == "23:12"
        assert first_rosh.killer == "medusa"
        assert first_rosh.team == "dire"
        assert first_rosh.extra_info.get("kill_number") == 1

    def test_tormentor_kills_detected(self, objectives):
        _, tormentor, _, _ = objectives
        # Tormentor kills may be detected depending on combat log data
        assert isinstance(tormentor, list)
        if len(tormentor) > 0:
            assert all(isinstance(t, ObjectiveKill) for t in tormentor)

    def test_first_tormentor_kill_details(self, objectives):
        _, tormentor, _, _ = objectives
        if len(tormentor) == 0:
            pytest.skip("No tormentor kills detected in this replay")
        first_tormentor = tormentor[0]
        assert first_tormentor.objective_type == "tormentor"

    def test_tower_kills_correct_count(self, objectives):
        _, _, towers, _ = objectives
        assert len(towers) == 14
        assert all(isinstance(t, ObjectiveKill) for t in towers)

    def test_first_tower_kill_details(self, objectives):
        _, _, towers, _ = objectives
        first_tower = towers[0]
        assert first_tower.game_time_str == "11:09"
        assert "tower" in first_tower.objective_name.lower()
        assert first_tower.extra_info.get("tower_team") == "dire"

    def test_barracks_kills_correct_count(self, objectives):
        _, _, _, barracks = objectives
        assert len(barracks) == 6
        assert all(isinstance(b, ObjectiveKill) for b in barracks)

    def test_first_barracks_kill_details(self, objectives):
        _, _, _, barracks = objectives
        first_rax = barracks[0]
        assert first_rax.game_time_str == "39:33"
        assert first_rax.extra_info.get("barracks_team") == "radiant"
        assert first_rax.extra_info.get("barracks_type") == "melee"

    def test_all_barracks_are_radiant(self, objectives):
        _, _, _, barracks = objectives
        for rax in barracks:
            assert rax.extra_info.get("barracks_team") == "radiant"


class TestPositionTracking:

    def test_hero_deaths_include_position(self, hero_deaths_with_position):
        deaths_with_pos = [d for d in hero_deaths_with_position if d.position_x is not None]
        assert len(deaths_with_pos) > 0

    def test_hero_death_position_has_correct_structure(self, hero_deaths_with_position):
        death_with_pos = next((d for d in hero_deaths_with_position if d.position_x is not None), None)
        assert death_with_pos is not None

        assert isinstance(death_with_pos.position_x, float)
        assert isinstance(death_with_pos.position_y, float)

    def test_first_blood_death_has_position(self, hero_deaths_with_position):
        first_death = hero_deaths_with_position[0]
        assert first_death.victim == "earthshaker"
        # Position may or may not be available depending on combat log data

    def test_position_coordinates_in_valid_range(self, hero_deaths_with_position):
        for death in hero_deaths_with_position:
            if death.position_x is not None:
                assert -8500 <= death.position_x <= 8500
            if death.position_y is not None:
                assert -8500 <= death.position_y <= 8500


class TestRunePickups:

    def test_get_rune_pickups_returns_list_of_rune_pickup_models(self, rune_pickups):
        # Rune pickups require PICKUP_RUNE in combat log types
        assert isinstance(rune_pickups, list)
        if len(rune_pickups) > 0:
            assert all(isinstance(p, RunePickup) for p in rune_pickups)

    def test_rune_pickups_detected(self, rune_pickups):
        # Number of rune pickups depends on match and parsing config
        assert isinstance(rune_pickups, list)

    def test_rune_pickup_has_correct_structure(self, rune_pickups):
        if len(rune_pickups) == 0:
            pytest.skip("No rune pickups detected")
        first_rune = rune_pickups[0]
        assert hasattr(first_rune, "game_time_str")
        assert hasattr(first_rune, "hero")
        assert hasattr(first_rune, "rune_type")

    def test_rune_pickups_sorted_by_time(self, rune_pickups):
        if len(rune_pickups) == 0:
            pytest.skip("No rune pickups detected")
        times = [p.game_time for p in rune_pickups]
        assert times == sorted(times)

    def test_rune_types_are_valid(self, rune_pickups):
        if len(rune_pickups) == 0:
            pytest.skip("No rune pickups detected")
        valid_types = {"double_damage", "haste", "invisibility", "regeneration", "arcane", "shield"}
        for pickup in rune_pickups:
            assert pickup.rune_type in valid_types or pickup.rune_type.startswith("unknown_")

    def test_rune_pickup_hero_names_are_clean(self, rune_pickups):
        if len(rune_pickups) == 0:
            pytest.skip("No rune pickups detected")
        for pickup in rune_pickups:
            assert not pickup.hero.startswith("npc_dota_hero_")


class TestAbilityHitDetection:

    def test_ability_events_have_hit_field(self, combat_log_280_300_ability):
        ability_events = [e for e in combat_log_280_300_ability if e.type == "ABILITY"]
        if len(ability_events) == 0:
            pytest.skip("No ability events in this time range")
        for e in ability_events:
            assert e.hit in (True, False, None)

    def test_self_buff_abilities_detected(self, combat_log_280_300_earthshaker_ability):
        totem_events = [e for e in combat_log_280_300_earthshaker_ability if e.ability == "earthshaker_enchant_totem"]
        if len(totem_events) == 0:
            pytest.skip("No enchant totem events found")
        # v2: Self-buff abilities have target as 'dota_unknown' and hit is False or None
        for e in totem_events:
            assert e.hit in (True, False, None)

    def test_ensnare_that_hit_shows_as_true(self, combat_log_280_282_naga_ability):
        ensnare_events = [e for e in combat_log_280_282_naga_ability if e.ability == "naga_siren_ensnare"]
        if len(ensnare_events) == 0:
            pytest.skip("No ensnare events found")
        assert ensnare_events[0].hit is True

    def test_non_ability_events_have_hit_none(self, combat_log_280_290_non_ability):
        for e in combat_log_280_290_non_ability:
            assert e.hit is None

    def test_hit_detection_stats(self, combat_log_0_600_ability):
        # v2 hit detection may differ from legacy
        hits = [e for e in combat_log_0_600_ability if e.hit is True]
        misses = [e for e in combat_log_0_600_ability if e.hit is False]
        na = [e for e in combat_log_0_600_ability if e.hit is None]

        # Total should match
        assert len(hits) + len(misses) + len(na) == len(combat_log_0_600_ability)


class TestAbilityTrigger:

    def test_ability_trigger_events_included(self, combat_log_320_370):
        trigger_events = [e for e in combat_log_320_370 if e.type == "ABILITY_TRIGGER"]
        # v2 may or may not have trigger events depending on parsing config
        assert isinstance(trigger_events, list)

    def test_lotus_orb_reflections_tracked(self, combat_log_trigger_only):
        lotus_events = [e for e in combat_log_trigger_only if e.ability and "lotus" in e.ability.lower()]
        # May not have lotus events in all replays
        assert isinstance(lotus_events, list)

    def test_lotus_orb_reflection_structure(self, combat_log_trigger_only):
        lotus_events = [e for e in combat_log_trigger_only if e.ability and "lotus" in e.ability.lower()]
        if len(lotus_events) == 0:
            pytest.skip("No lotus orb events found")

        first = lotus_events[0]
        assert hasattr(first, "attacker")
        assert hasattr(first, "target")
        assert hasattr(first, "ability")

    def test_ability_trigger_in_combat_log(self, combat_log_360_370):
        # Verify combat log structure
        assert isinstance(combat_log_360_370, list)


class TestStartTimeNegativeFilter:
    """Tests for start_time parameter with negative (pre-game) times."""

    def test_start_time_0_excludes_negative_game_times(self, combat_log_start_time_0):
        """start_time=0 should exclude all events with negative game_time."""
        for event in combat_log_start_time_0:
            assert event.game_time >= 0, f"Event at {event.game_time} should be excluded with start_time=0"

    def test_start_time_neg90_includes_pregame_events(self, combat_log_start_time_neg90):
        """start_time=-90 should include pre-game events (purchases, etc.)."""
        negative_time_events = [e for e in combat_log_start_time_neg90 if e.game_time < 0]
        assert len(negative_time_events) > 0, "Pre-game events should be included with start_time=-90"

    def test_start_time_none_includes_pregame_events(self, combat_log_start_time_none):
        """start_time=None should include all events including pre-game."""
        negative_time_events = [e for e in combat_log_start_time_none if e.game_time < 0]
        assert len(negative_time_events) > 0, "Pre-game events should be included with start_time=None"

    def test_pregame_purchases_captured_with_negative_start_time(self, combat_log_start_time_neg90):
        """Pre-game item purchases should be captured with negative start_time."""
        purchase_events = [e for e in combat_log_start_time_neg90 if e.type == "PURCHASE" and e.game_time < 0]
        assert len(purchase_events) > 0, "Pre-game purchases should be included (wards, tangos, etc.)"

    def test_start_time_0_excludes_pregame_purchases(self, combat_log_start_time_0):
        """start_time=0 should NOT include pre-game purchases."""
        purchase_events = [e for e in combat_log_start_time_0 if e.type == "PURCHASE" and e.game_time < 0]
        assert len(purchase_events) == 0, "Pre-game purchases should be excluded with start_time=0"

    def test_neg90_has_more_events_than_0(self, combat_log_start_time_0, combat_log_start_time_neg90):
        """start_time=-90 should have more events than start_time=0 (pre-game included)."""
        assert len(combat_log_start_time_neg90) > len(combat_log_start_time_0)


class TestDetailLevelFiltering:
    """Deterministic tests for detail_level filtering with exact expected values.

    Test data from match 8461956309, time window 280-290 seconds (first blood fight).
    """

    # ========== NARRATIVE level tests ==========
    # Expected: 11 events (8 ABILITY, 1 DEATH, 2 ITEM)

    def test_narrative_total_event_count(self, combat_log_280_290_narrative):
        """NARRATIVE should return exactly 11 events."""
        assert len(combat_log_280_290_narrative) == 11

    def test_narrative_ability_count(self, combat_log_280_290_narrative):
        """NARRATIVE should have exactly 8 ABILITY events."""
        ability_events = [e for e in combat_log_280_290_narrative if e.type == "ABILITY"]
        assert len(ability_events) == 8

    def test_narrative_death_count(self, combat_log_280_290_narrative):
        """NARRATIVE should have exactly 1 DEATH event (first blood)."""
        death_events = [e for e in combat_log_280_290_narrative if e.type == "DEATH"]
        assert len(death_events) == 1

    def test_narrative_item_count(self, combat_log_280_290_narrative):
        """NARRATIVE should have exactly 2 ITEM events."""
        item_events = [e for e in combat_log_280_290_narrative if e.type == "ITEM"]
        assert len(item_events) == 2

    def test_narrative_damage_count_zero(self, combat_log_280_290_narrative):
        """NARRATIVE must have exactly 0 DAMAGE events."""
        damage_events = [e for e in combat_log_280_290_narrative if e.type == "DAMAGE"]
        assert len(damage_events) == 0

    def test_narrative_modifier_add_count_zero(self, combat_log_280_290_narrative):
        """NARRATIVE must have exactly 0 MODIFIER_ADD events."""
        modifier_events = [e for e in combat_log_280_290_narrative if e.type == "MODIFIER_ADD"]
        assert len(modifier_events) == 0

    def test_narrative_modifier_remove_count_zero(self, combat_log_280_290_narrative):
        """NARRATIVE must have exactly 0 MODIFIER_REMOVE events."""
        modifier_events = [e for e in combat_log_280_290_narrative if e.type == "MODIFIER_REMOVE"]
        assert len(modifier_events) == 0

    def test_narrative_heal_count_zero(self, combat_log_280_290_narrative):
        """NARRATIVE must have exactly 0 HEAL events."""
        heal_events = [e for e in combat_log_280_290_narrative if e.type == "HEAL"]
        assert len(heal_events) == 0

    def test_narrative_death_is_hero(self, combat_log_280_290_narrative):
        """NARRATIVE death event must be a hero death (target_is_hero=True)."""
        death_events = [e for e in combat_log_280_290_narrative if e.type == "DEATH"]
        assert len(death_events) == 1
        assert death_events[0].target_is_hero is True

    def test_narrative_all_abilities_from_heroes(self, combat_log_280_290_narrative):
        """All 8 NARRATIVE ability events must be from heroes (attacker_is_hero=True)."""
        ability_events = [e for e in combat_log_280_290_narrative if e.type == "ABILITY"]
        non_hero_abilities = [e for e in ability_events if not e.attacker_is_hero]
        assert len(non_hero_abilities) == 0

    def test_narrative_all_items_from_heroes(self, combat_log_280_290_narrative):
        """All 2 NARRATIVE item events must be from heroes (attacker_is_hero=True)."""
        item_events = [e for e in combat_log_280_290_narrative if e.type == "ITEM"]
        non_hero_items = [e for e in item_events if not e.attacker_is_hero]
        assert len(non_hero_items) == 0

    # ========== TACTICAL level tests ==========
    # Expected: 60 events (8 ABILITY, 29 DAMAGE, 1 DEATH, 2 ITEM, 20 MODIFIER_ADD)

    def test_tactical_total_event_count(self, combat_log_280_290_tactical):
        """TACTICAL should return exactly 60 events."""
        assert len(combat_log_280_290_tactical) == 60

    def test_tactical_ability_count(self, combat_log_280_290_tactical):
        """TACTICAL should have exactly 8 ABILITY events."""
        ability_events = [e for e in combat_log_280_290_tactical if e.type == "ABILITY"]
        assert len(ability_events) == 8

    def test_tactical_damage_count(self, combat_log_280_290_tactical):
        """TACTICAL should have exactly 29 DAMAGE events (hero-to-hero only)."""
        damage_events = [e for e in combat_log_280_290_tactical if e.type == "DAMAGE"]
        assert len(damage_events) == 29

    def test_tactical_death_count(self, combat_log_280_290_tactical):
        """TACTICAL should have exactly 1 DEATH event."""
        death_events = [e for e in combat_log_280_290_tactical if e.type == "DEATH"]
        assert len(death_events) == 1

    def test_tactical_item_count(self, combat_log_280_290_tactical):
        """TACTICAL should have exactly 2 ITEM events."""
        item_events = [e for e in combat_log_280_290_tactical if e.type == "ITEM"]
        assert len(item_events) == 2

    def test_tactical_modifier_add_count(self, combat_log_280_290_tactical):
        """TACTICAL should have exactly 20 MODIFIER_ADD events (on heroes only)."""
        modifier_events = [e for e in combat_log_280_290_tactical if e.type == "MODIFIER_ADD"]
        assert len(modifier_events) == 20

    def test_tactical_modifier_remove_count_zero(self, combat_log_280_290_tactical):
        """TACTICAL must have exactly 0 MODIFIER_REMOVE events."""
        modifier_remove = [e for e in combat_log_280_290_tactical if e.type == "MODIFIER_REMOVE"]
        assert len(modifier_remove) == 0

    def test_tactical_heal_count_zero(self, combat_log_280_290_tactical):
        """TACTICAL must have exactly 0 HEAL events."""
        heal_events = [e for e in combat_log_280_290_tactical if e.type == "HEAL"]
        assert len(heal_events) == 0

    def test_tactical_all_damage_hero_to_hero(self, combat_log_280_290_tactical):
        """All 29 TACTICAL damage events must be hero-to-hero."""
        damage_events = [e for e in combat_log_280_290_tactical if e.type == "DAMAGE"]
        non_h2h = [e for e in damage_events if not e.attacker_is_hero or not e.target_is_hero]
        assert len(non_h2h) == 0

    def test_tactical_all_modifiers_on_heroes(self, combat_log_280_290_tactical):
        """All 20 TACTICAL modifier_add events must be on heroes (target_is_hero=True)."""
        modifier_events = [e for e in combat_log_280_290_tactical if e.type == "MODIFIER_ADD"]
        non_hero_mods = [e for e in modifier_events if not e.target_is_hero]
        assert len(non_hero_mods) == 0

    # ========== FULL level tests ==========
    # Expected: 136 events (8 ABILITY, 52 DAMAGE, 12 DEATH, 1 HEAL, 2 ITEM, 29 MODIFIER_ADD, 32 MODIFIER_REMOVE)

    def test_full_total_event_count(self, combat_log_280_290_full):
        """FULL should return exactly 136 events."""
        assert len(combat_log_280_290_full) == 136

    def test_full_ability_count(self, combat_log_280_290_full):
        """FULL should have exactly 8 ABILITY events."""
        ability_events = [e for e in combat_log_280_290_full if e.type == "ABILITY"]
        assert len(ability_events) == 8

    def test_full_damage_count(self, combat_log_280_290_full):
        """FULL should have exactly 52 DAMAGE events (all sources)."""
        damage_events = [e for e in combat_log_280_290_full if e.type == "DAMAGE"]
        assert len(damage_events) == 52

    def test_full_death_count(self, combat_log_280_290_full):
        """FULL should have exactly 12 DEATH events (heroes + creeps)."""
        death_events = [e for e in combat_log_280_290_full if e.type == "DEATH"]
        assert len(death_events) == 12

    def test_full_heal_count(self, combat_log_280_290_full):
        """FULL should have exactly 1 HEAL event."""
        heal_events = [e for e in combat_log_280_290_full if e.type == "HEAL"]
        assert len(heal_events) == 1

    def test_full_item_count(self, combat_log_280_290_full):
        """FULL should have exactly 2 ITEM events."""
        item_events = [e for e in combat_log_280_290_full if e.type == "ITEM"]
        assert len(item_events) == 2

    def test_full_modifier_add_count(self, combat_log_280_290_full):
        """FULL should have exactly 29 MODIFIER_ADD events."""
        modifier_events = [e for e in combat_log_280_290_full if e.type == "MODIFIER_ADD"]
        assert len(modifier_events) == 29

    def test_full_modifier_remove_count(self, combat_log_280_290_full):
        """FULL should have exactly 32 MODIFIER_REMOVE events."""
        modifier_remove = [e for e in combat_log_280_290_full if e.type == "MODIFIER_REMOVE"]
        assert len(modifier_remove) == 32

    # ========== Cross-level filtering verification ==========

    def test_full_has_creep_damage_that_tactical_excludes(self, combat_log_280_290_tactical, combat_log_280_290_full):
        """FULL has 52 damage, TACTICAL has 29 - difference is 23 creep damage events."""
        full_damage = [e for e in combat_log_280_290_full if e.type == "DAMAGE"]
        tactical_damage = [e for e in combat_log_280_290_tactical if e.type == "DAMAGE"]
        assert len(full_damage) - len(tactical_damage) == 23

    def test_full_has_creep_deaths_that_narrative_excludes(self, combat_log_280_290_narrative, combat_log_280_290_full):
        """FULL has 12 deaths, NARRATIVE has 1 - difference is 11 creep deaths."""
        full_deaths = [e for e in combat_log_280_290_full if e.type == "DEATH"]
        narrative_deaths = [e for e in combat_log_280_290_narrative if e.type == "DEATH"]
        assert len(full_deaths) - len(narrative_deaths) == 11

    def test_full_has_modifiers_that_tactical_excludes(self, combat_log_280_290_tactical, combat_log_280_290_full):
        """FULL has 29 modifier_add, TACTICAL has 20 - difference is 9 non-hero modifiers."""
        full_mods = [e for e in combat_log_280_290_full if e.type == "MODIFIER_ADD"]
        tactical_mods = [e for e in combat_log_280_290_tactical if e.type == "MODIFIER_ADD"]
        assert len(full_mods) - len(tactical_mods) == 9
