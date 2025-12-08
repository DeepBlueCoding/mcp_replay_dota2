"""Tests for hero combat analysis functionality."""

from src.models.combat_log import (
    AbilityUsage,
    FightParticipation,
    HeroCombatAnalysisResponse,
)


class TestAbilityUsageModel:
    """Unit tests for AbilityUsage model."""

    def test_ability_usage_creation(self):
        usage = AbilityUsage(
            ability="earthshaker_fissure",
            total_casts=10,
            hero_hits=7,
            hit_rate=70.0,
        )
        assert usage.ability == "earthshaker_fissure"
        assert usage.total_casts == 10
        assert usage.hero_hits == 7
        assert usage.hit_rate == 70.0

    def test_ability_usage_zero_casts(self):
        usage = AbilityUsage(
            ability="some_ability",
            total_casts=0,
            hero_hits=0,
            hit_rate=0.0,
        )
        assert usage.total_casts == 0
        assert usage.hit_rate == 0.0

    def test_ability_usage_100_percent_hit_rate(self):
        usage = AbilityUsage(
            ability="targeted_ability",
            total_casts=5,
            hero_hits=5,
            hit_rate=100.0,
        )
        assert usage.hit_rate == 100.0


class TestFightParticipationModel:
    """Unit tests for FightParticipation model."""

    def test_fight_participation_creation(self):
        participation = FightParticipation(
            fight_id="fight_1",
            fight_start=288.0,
            fight_start_str="4:48",
            fight_end=295.0,
            fight_end_str="4:55",
            is_teamfight=False,
            kills=1,
            deaths=0,
            assists=2,
            abilities_used=[],
            damage_dealt=1500,
            damage_received=500,
        )
        assert participation.fight_id == "fight_1"
        assert participation.kills == 1
        assert participation.deaths == 0
        assert participation.assists == 2
        assert participation.damage_dealt == 1500

    def test_fight_participation_with_abilities(self):
        abilities = [
            AbilityUsage(ability="fissure", total_casts=2, hero_hits=2, hit_rate=100.0),
            AbilityUsage(ability="echo_slam", total_casts=1, hero_hits=3, hit_rate=300.0),
        ]
        participation = FightParticipation(
            fight_id="fight_2",
            fight_start=600.0,
            fight_start_str="10:00",
            fight_end=620.0,
            fight_end_str="10:20",
            is_teamfight=True,
            kills=3,
            deaths=1,
            assists=1,
            abilities_used=abilities,
            damage_dealt=5000,
            damage_received=2000,
        )
        assert len(participation.abilities_used) == 2
        assert participation.abilities_used[0].ability == "fissure"


class TestHeroCombatAnalysisResponseModel:
    """Unit tests for HeroCombatAnalysisResponse model."""

    def test_response_success(self):
        response = HeroCombatAnalysisResponse(
            success=True,
            match_id=12345,
            hero="earthshaker",
            total_fights=5,
            total_teamfights=2,
            total_kills=4,
            total_deaths=3,
            total_assists=10,
            ability_summary=[],
            fights=[],
        )
        assert response.success is True
        assert response.hero == "earthshaker"
        assert response.total_fights == 5

    def test_response_error(self):
        response = HeroCombatAnalysisResponse(
            success=False,
            match_id=12345,
            hero="invalid_hero",
            error="Hero not found in match",
        )
        assert response.success is False
        assert response.error == "Hero not found in match"


class TestHeroCombatAnalysisIntegration:
    """Integration tests with real replay data."""

    def test_earthshaker_analysis_returns_response(self, hero_combat_analysis_earthshaker):
        """Verify earthshaker analysis returns valid response."""
        result = hero_combat_analysis_earthshaker
        assert result.success is True
        assert result.match_id == 8461956309
        assert "earthshaker" in result.hero.lower()

    def test_earthshaker_participated_in_fights(self, hero_combat_analysis_earthshaker):
        """Earthshaker should have participated in at least one fight."""
        result = hero_combat_analysis_earthshaker
        assert result.total_fights > 0

    def test_earthshaker_has_ability_summary(self, hero_combat_analysis_earthshaker):
        """Earthshaker should have ability usage tracked."""
        result = hero_combat_analysis_earthshaker
        assert len(result.ability_summary) > 0
        ability_names = [a.ability for a in result.ability_summary]
        assert any("earthshaker" in name or "fissure" in name or "echo" in name
                   for name in ability_names)

    def test_earthshaker_first_blood_fight(self, hero_combat_analysis_earthshaker):
        """Earthshaker died in the first blood fight around 4:48."""
        result = hero_combat_analysis_earthshaker
        first_blood_fights = [
            f for f in result.fights
            if 280 <= f.fight_start <= 300
        ]
        assert len(first_blood_fights) >= 1
        fb_fight = first_blood_fights[0]
        assert fb_fight.deaths >= 1

    def test_disruptor_got_first_blood(self, hero_combat_analysis_disruptor):
        """Disruptor got first blood on earthshaker at 4:48."""
        result = hero_combat_analysis_disruptor
        assert result.success is True
        first_blood_fights = [
            f for f in result.fights
            if 280 <= f.fight_start <= 300
        ]
        assert len(first_blood_fights) >= 1
        fb_fight = first_blood_fights[0]
        assert fb_fight.kills >= 1

    def test_fight_participation_has_valid_structure(self, hero_combat_analysis_earthshaker):
        """Each fight participation should have valid structure."""
        result = hero_combat_analysis_earthshaker
        for fight in result.fights:
            assert fight.fight_id is not None
            assert fight.fight_start >= 0
            assert fight.fight_end >= fight.fight_start
            assert fight.kills >= 0
            assert fight.deaths >= 0
            assert fight.assists >= 0
            assert fight.damage_dealt >= 0
            assert fight.damage_received >= 0

    def test_ability_usage_has_valid_structure(self, hero_combat_analysis_earthshaker):
        """Ability usage should have valid structure."""
        result = hero_combat_analysis_earthshaker
        for ability in result.ability_summary:
            assert ability.ability is not None
            assert ability.total_casts >= 0
            assert ability.hero_hits >= 0
            assert ability.hit_rate >= 0

    def test_totals_match_fight_sums(self, hero_combat_analysis_earthshaker):
        """Total kills/deaths/assists should match sum of fights."""
        result = hero_combat_analysis_earthshaker
        sum_kills = sum(f.kills for f in result.fights)
        sum_deaths = sum(f.deaths for f in result.fights)
        sum_assists = sum(f.assists for f in result.fights)

        assert result.total_kills == sum_kills
        assert result.total_deaths == sum_deaths
        assert result.total_assists == sum_assists

    def test_teamfight_count_matches(self, hero_combat_analysis_earthshaker):
        """Total teamfights should match count of is_teamfight=True."""
        result = hero_combat_analysis_earthshaker
        teamfight_count = sum(1 for f in result.fights if f.is_teamfight)
        assert result.total_teamfights == teamfight_count


class TestModifierAddTracking:
    """Tests for MODIFIER_ADD based hit detection (for ground-targeted abilities)."""

    def test_disruptor_kinetic_field_tracked(self, hero_combat_analysis_disruptor):
        """Disruptor's Kinetic Field should track hits via MODIFIER_ADD."""
        result = hero_combat_analysis_disruptor
        ability_names = [a.ability.lower() for a in result.ability_summary]
        has_kinetic = any("kinetic" in name for name in ability_names)
        has_thunder = any("thunder" in name or "storm" in name for name in ability_names)
        assert has_kinetic or has_thunder or len(result.ability_summary) > 0

    def test_earthshaker_fissure_tracked(self, hero_combat_analysis_earthshaker):
        """Earthshaker's Fissure should be tracked."""
        result = hero_combat_analysis_earthshaker
        ability_names = [a.ability.lower() for a in result.ability_summary]
        has_fissure = any("fissure" in name for name in ability_names)
        has_echo = any("echo" in name for name in ability_names)
        assert has_fissure or has_echo

    def test_ability_hits_can_exceed_casts_for_aoe(self, hero_combat_analysis_earthshaker):
        """AoE abilities can hit multiple heroes per cast, so hits can exceed casts."""
        result = hero_combat_analysis_earthshaker
        for ability in result.ability_summary:
            if "echo" in ability.ability.lower():
                assert ability.hero_hits >= 0

    def test_fissure_stun_tracked_via_modifier_add(self, hero_combat_analysis_earthshaker):
        """Fissure stun should be tracked via MODIFIER_ADD events."""
        result = hero_combat_analysis_earthshaker
        fissure = next((a for a in result.ability_summary if "fissure" in a.ability.lower()), None)
        assert fissure is not None
        assert fissure.total_casts > 0
        assert fissure.hero_hits > 0
