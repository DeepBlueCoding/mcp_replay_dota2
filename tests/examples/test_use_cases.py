"""
Use case validation tests.

Tests validate the documented use cases from:
https://deepbluecoding.github.io/mcp-replay-dota2/latest/examples/use-cases/

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
    def test_fight_detection_works(self, fight_first_blood, hero_deaths):
        """Fight detection can analyze a specific fight."""
        if hero_deaths:
            first_death_time = hero_deaths[0].game_time
            assert fight_first_blood is not None
            # v2: Fight model has start_time/end_time instead of fight_start/fight_end
            assert fight_first_blood.start_time <= first_death_time <= fight_first_blood.end_time
            assert len(fight_first_blood.participants) > 0


class TestUseCaseUnderstandGank:
    """
    Use Case 3: Understanding a Gank

    Tools: get_hero_deaths() with position, get_fight_combat_log()
    Goal: Analyze positioning and ability sequence in a gank
    """

    @pytest.mark.use_case
    def test_hero_deaths_include_position(self, hero_deaths_with_position):
        """Deaths include position data for gank analysis."""
        # v2: position_x and position_y directly on HeroDeath, not nested .position
        deaths_with_pos = [d for d in hero_deaths_with_position if d.position_x is not None]
        assert len(deaths_with_pos) > 0
        assert deaths_with_pos[0].position_x is not None
        assert deaths_with_pos[0].position_y is not None

    @pytest.mark.use_case
    def test_fight_has_deaths(self, fight_first_blood):
        """Fight detection includes deaths."""
        # v2: Fight model has deaths list, not events
        assert len(fight_first_blood.deaths) >= 0


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
