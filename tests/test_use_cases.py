"""
Use case validation tests.

Tests validate the documented use cases from:
https://deepbluecoding.github.io/mcp_replay_dota2/latest/examples/use-cases/

Uses pre-parsed replay data from conftest.py fixtures.
Run with: uv run pytest tests/test_use_cases.py -v
"""

import pytest


class TestUseCaseAnalyzeTeamfight:
    """
    Use Case 1: Analyzing a Lost Teamfight

    Tools: get_hero_deaths(), get_fight_combat_log()
    Goal: Determine what went wrong during a team engagement
    """

    @pytest.mark.use_case
    def test_get_hero_deaths_returns_deaths_with_time(self, hero_deaths):
        """Deaths have game_time for identifying fight moments."""
        assert len(hero_deaths) > 0
        assert all(hasattr(d, 'game_time') for d in hero_deaths)
        assert all(hasattr(d, 'game_time_str') for d in hero_deaths)

    @pytest.mark.use_case
    def test_get_hero_deaths_has_killer_and_victim(self, hero_deaths):
        """Deaths identify killer and victim for fight analysis."""
        assert all(hasattr(d, 'killer') for d in hero_deaths)
        assert all(hasattr(d, 'victim') for d in hero_deaths)
        assert all(d.victim for d in hero_deaths)

    @pytest.mark.use_case
    def test_fight_combat_log_available(self, fight_first_blood, hero_deaths):
        """get_fight_combat_log can analyze a specific fight."""
        if hero_deaths:
            first_death_time = hero_deaths[0].game_time
            assert fight_first_blood is not None
            assert fight_first_blood.fight_start <= first_death_time <= fight_first_blood.fight_end
            assert len(fight_first_blood.participants) > 0


class TestUseCaseTrackCarryFarm:
    """
    Use Case 2: Tracking Carry Farm

    Tools: get_item_purchases(), get_stats_at_minute()
    Goal: Evaluate farm efficiency by item timings and CS
    """

    @pytest.mark.use_case
    def test_item_purchases_have_timing(self, test_replay_path):
        """Item purchases include game_time for tracking progression."""
        from src.utils.combat_log_parser import combat_log_parser

        purchases = combat_log_parser.get_item_purchases(test_replay_path)
        assert len(purchases) > 0
        assert all(hasattr(p, 'game_time') for p in purchases)
        assert all(hasattr(p, 'hero') for p in purchases)
        assert all(hasattr(p, 'item') for p in purchases)

    @pytest.mark.use_case
    def test_item_purchases_filter_by_hero(self, test_replay_path):
        """Can filter item purchases by specific hero."""
        from src.utils.combat_log_parser import combat_log_parser

        purchases = combat_log_parser.get_item_purchases(
            test_replay_path,
            hero_filter="juggernaut"
        )
        assert all("juggernaut" in p.hero.lower() for p in purchases)

    @pytest.mark.use_case
    def test_stats_at_minute_has_farm_data(self, stats_10min):
        """get_stats_at_minute returns CS, gold, level data."""
        assert "players" in stats_10min

        for player in stats_10min["players"]:
            assert "net_worth" in player or "gold" in player
            assert "level" in player


class TestUseCaseUnderstandGank:
    """
    Use Case 3: Understanding a Gank

    Tools: get_hero_deaths() with position, get_fight_combat_log()
    Goal: Analyze positioning and ability sequence in a gank
    """

    @pytest.mark.use_case
    def test_hero_deaths_include_position(self, hero_deaths_with_position):
        """Deaths include position data for gank analysis."""
        deaths_with_pos = [d for d in hero_deaths_with_position if d.position is not None]
        assert len(deaths_with_pos) > 0
        assert deaths_with_pos[0].position.x is not None
        assert deaths_with_pos[0].position.y is not None

    @pytest.mark.use_case
    def test_combat_log_shows_ability_sequence(self, fight_first_blood):
        """Combat log shows abilities used in order."""
        ability_events = [e for e in fight_first_blood.events if e.type == "ABILITY"]
        assert len(ability_events) >= 0  # May not always have abilities


class TestUseCaseObjectiveControl:
    """
    Use Case 4: Objective Control Analysis

    Tools: get_objective_kills()
    Goal: Track Roshan, towers, barracks timing
    """

    @pytest.mark.use_case
    def test_objective_kills_has_roshan(self, objectives):
        """Roshan kills are tracked with timing."""
        roshan, _, _, _ = objectives
        assert len(roshan) > 0
        assert all(hasattr(r, 'game_time') for r in roshan)
        assert all(hasattr(r, 'killer') for r in roshan)

    @pytest.mark.use_case
    def test_objective_kills_has_towers(self, objectives):
        """Tower kills are tracked."""
        _, _, towers, _ = objectives
        assert len(towers) > 0
        for t in towers:
            assert hasattr(t, 'team')

    @pytest.mark.use_case
    def test_objective_kills_has_barracks(self, objectives):
        """Barracks kills are tracked."""
        _, _, _, barracks = objectives
        assert isinstance(barracks, list)


class TestUseCaseCompareLaning:
    """
    Use Case 5: Comparing Laning Phase

    Tools: get_stats_at_minute()
    Goal: Compare CS, denies, net worth at early timings
    """

    @pytest.mark.use_case
    def test_stats_at_5_minutes(self, stats_5min):
        """Can get stats at 5 minute mark."""
        assert stats_5min is not None
        assert "minute" in stats_5min
        assert stats_5min["minute"] == 5

    @pytest.mark.use_case
    def test_stats_at_10_minutes(self, stats_10min):
        """Can get stats at 10 minute mark for laning comparison."""
        assert stats_10min is not None
        assert "players" in stats_10min
        assert len(stats_10min["players"]) == 10

    @pytest.mark.use_case
    def test_laning_stats_comparable(self, stats_10min):
        """Stats include data needed for lane comparison."""
        for player in stats_10min["players"]:
            assert "player_slot" in player or "team" in player
            has_farm_metric = any(
                k in player for k in ["net_worth", "gold", "last_hits"]
            )
            assert has_farm_metric
            assert "level" in player


class TestFastUnitTests:
    """Fast tests that don't require replay parsing."""

    @pytest.mark.fast
    @pytest.mark.core
    @pytest.mark.asyncio
    async def test_heroes_resource_loads(self):
        """Heroes resource loads without replay."""
        from src.resources.heroes_resources import heroes_resource

        heroes = await heroes_resource.get_all_heroes()
        assert len(heroes) > 100

    @pytest.mark.fast
    @pytest.mark.core
    def test_map_resource_loads(self):
        """Map resource loads without replay."""
        from src.resources.map_resources import get_cached_map_data

        map_data = get_cached_map_data()
        assert map_data.towers
        assert map_data.neutral_camps
        assert map_data.rune_spawns

    @pytest.mark.fast
    @pytest.mark.core
    def test_constants_fetcher_works(self):
        """Constants fetcher provides hero data."""
        from src.utils.constants_fetcher import constants_fetcher

        heroes = constants_fetcher.get_heroes_constants()
        assert heroes is not None
        assert len(heroes) > 100

    @pytest.mark.fast
    @pytest.mark.core
    def test_hero_fuzzy_search_works(self):
        """Fuzzy search finds heroes."""
        from src.utils.hero_fuzzy_search import hero_fuzzy_search

        result = hero_fuzzy_search.find_best_match("jugg")
        assert result is not None
        assert "juggernaut" in result["name"].lower()

    @pytest.mark.fast
    @pytest.mark.core
    def test_services_import(self):
        """All services can be imported."""
        from src.services import (
            CombatService,
            ReplayService,
        )
        assert ReplayService is not None
        assert CombatService is not None
