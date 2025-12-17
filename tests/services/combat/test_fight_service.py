"""
Tests for FightService.

Uses pre-parsed replay data from conftest.py fixtures.
All data is from match 8461956309 with verified values from Dotabuff.
"""

from src.services.models.combat_data import Fight, HeroDeath


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
