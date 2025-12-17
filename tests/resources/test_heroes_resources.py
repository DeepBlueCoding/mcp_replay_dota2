"""
Test suite for heroes_resources.py

Following CLAUDE.md testing principles:
- Test against REAL EXPECTED VALUES from actual data
- Use Golden Master approach with verified values
- Test business logic correctness with real inputs
- No framework behavior testing, only actual business value
"""

import pytest

from src.resources.heroes_resources import HeroesResource

# Real test data - these are VERIFIED values from actual dotaconstants
EXPECTED_TOTAL_HEROES = 126  # Actual count from dotaconstants

# Known heroes with their exact data for golden master testing (from dotaconstants)
# Note: Counter data is dynamic, so we test for presence of fields rather than exact values

REQUIRED_HERO_FIELDS = {"hero_id", "canonical_name", "aliases", "attribute", "counters", "good_against", "when_to_pick"}

KNOWN_ABADDON_BASE = {
    "hero_id": 102,
    "canonical_name": "Abaddon",
    "aliases": ["abaddon"],
    "attribute": "universal"
}

KNOWN_ANTI_MAGE_BASE = {
    "hero_id": 1,
    "canonical_name": "Anti-Mage",
    "aliases": ["anti-mage", "antimage"],
    "attribute": "agility"
}

KNOWN_ZEUS_BASE = {
    "hero_id": 22,
    "canonical_name": "Zeus",
    "aliases": ["zeus"],
    "attribute": "intelligence"
}

# Expected hero internal names for specific heroes (from dotaconstants)
EXPECTED_ABADDON_KEY = "npc_dota_hero_abaddon"
EXPECTED_ANTI_MAGE_KEY = "npc_dota_hero_antimage"
EXPECTED_ZEUS_KEY = "npc_dota_hero_zuus"


class TestHeroesResource:
    """Test suite for HeroesResource business logic."""

    @pytest.fixture
    def heroes_resource(self):
        """Fixture that provides a HeroesResource instance."""
        return HeroesResource()

    def test_heroes_constants_loads_successfully(self, heroes_resource):
        """Test that heroes constants loads from dotaconstants."""
        heroes_constants = heroes_resource.get_heroes_constants_raw()

        assert isinstance(heroes_constants, dict)
        assert len(heroes_constants) > 0

    @pytest.mark.asyncio
    async def test_get_all_heroes_returns_exact_count(self, heroes_resource):
        """Test that get_all_heroes returns the exact expected count."""
        all_heroes = await heroes_resource.get_all_heroes()

        assert len(all_heroes) == EXPECTED_TOTAL_HEROES

    @pytest.mark.asyncio
    async def test_get_all_heroes_contains_known_heroes(self, heroes_resource):
        """Test that get_all_heroes contains known heroes with correct base data and counter fields."""
        all_heroes = await heroes_resource.get_all_heroes()

        assert EXPECTED_ABADDON_KEY in all_heroes
        abaddon = all_heroes[EXPECTED_ABADDON_KEY]
        for key, value in KNOWN_ABADDON_BASE.items():
            assert abaddon[key] == value
        assert set(abaddon.keys()) == REQUIRED_HERO_FIELDS

        assert EXPECTED_ANTI_MAGE_KEY in all_heroes
        anti_mage = all_heroes[EXPECTED_ANTI_MAGE_KEY]
        for key, value in KNOWN_ANTI_MAGE_BASE.items():
            assert anti_mage[key] == value
        assert set(anti_mage.keys()) == REQUIRED_HERO_FIELDS
        assert len(anti_mage["counters"]) > 0

        assert EXPECTED_ZEUS_KEY in all_heroes
        zeus = all_heroes[EXPECTED_ZEUS_KEY]
        for key, value in KNOWN_ZEUS_BASE.items():
            assert zeus[key] == value
        assert set(zeus.keys()) == REQUIRED_HERO_FIELDS

    @pytest.mark.asyncio
    async def test_get_all_heroes_has_all_required_attributes(self, heroes_resource):
        """Test that every hero has all required attributes including counter data."""
        all_heroes = await heroes_resource.get_all_heroes()

        for hero_key, hero_data in all_heroes.items():
            assert set(hero_data.keys()) == REQUIRED_HERO_FIELDS

            assert isinstance(hero_data["hero_id"], int)
            assert hero_data["hero_id"] > 0

            assert isinstance(hero_data["canonical_name"], str)
            assert len(hero_data["canonical_name"]) > 0

            assert isinstance(hero_data["aliases"], list)
            assert len(hero_data["aliases"]) > 0

            assert hero_data["attribute"] in ["strength", "agility", "intelligence", "universal"]

            assert isinstance(hero_data["counters"], list)
            assert isinstance(hero_data["good_against"], list)
            assert isinstance(hero_data["when_to_pick"], list)

    @pytest.mark.asyncio
    async def test_get_all_heroes_returns_copy_not_reference(self, heroes_resource):
        """Test that get_all_heroes returns a copy, not the original data."""
        heroes1 = await heroes_resource.get_all_heroes()
        heroes2 = await heroes_resource.get_all_heroes()

        assert heroes1 == heroes2
        assert heroes1 is not heroes2

        heroes1["test_key"] = {"test": "data"}

        heroes3 = await heroes_resource.get_all_heroes()
        assert "test_key" not in heroes3

    @pytest.mark.asyncio
    async def test_all_hero_ids_are_unique(self, heroes_resource):
        """Test that all heroes have unique IDs."""
        all_heroes = await heroes_resource.get_all_heroes()

        hero_ids = [hero_data["hero_id"] for hero_data in all_heroes.values()]

        assert len(hero_ids) == len(set(hero_ids))

    @pytest.mark.asyncio
    async def test_attribute_distribution_is_realistic(self, heroes_resource):
        """Test that hero attribute distribution matches expected ranges."""
        all_heroes = await heroes_resource.get_all_heroes()

        attribute_counts = {"strength": 0, "agility": 0, "intelligence": 0, "universal": 0}
        for hero_data in all_heroes.values():
            attribute_counts[hero_data["attribute"]] += 1

        assert attribute_counts["strength"] == 35
        assert attribute_counts["agility"] == 34
        assert attribute_counts["intelligence"] == 34
        assert attribute_counts["universal"] == 23

        total_by_attribute = sum(attribute_counts.values())
        assert total_by_attribute == EXPECTED_TOTAL_HEROES

    @pytest.mark.asyncio
    async def test_heroes_have_realistic_aliases(self, heroes_resource):
        """Test that heroes have realistic alias patterns."""
        all_heroes = await heroes_resource.get_all_heroes()

        for hero_key, hero_data in all_heroes.items():
            aliases = hero_data["aliases"]
            canonical_name = hero_data["canonical_name"]

            first_alias = aliases[0].lower()
            canonical_lower = canonical_name.lower()

            if " " not in canonical_name:
                assert first_alias == canonical_lower or canonical_lower.startswith(first_alias)


class TestHeroesResourceWithRealMatch:
    """Test suite for match-specific hero functionality with real match data."""

    @pytest.fixture
    def heroes_resource(self):
        """Fixture that provides a HeroesResource instance."""
        return HeroesResource()

    REAL_MATCH_ID = 8461956309

    EXPECTED_MATCH_HEROES = {
        "npc_dota_hero_earthshaker",
        "npc_dota_hero_magnataur",
        "npc_dota_hero_juggernaut",
        "npc_dota_hero_medusa",
        "npc_dota_hero_naga_siren",
        "npc_dota_hero_pangolier",
        "npc_dota_hero_nevermore",
        "npc_dota_hero_disruptor",
        "npc_dota_hero_pugna",
        "npc_dota_hero_shadow_demon"
    }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_heroes_in_match_returns_exactly_ten_heroes(self, heroes_resource):
        """Test that get_heroes_in_match returns exactly 10 heroes for a real match."""
        match_heroes = await heroes_resource.get_heroes_in_match(self.REAL_MATCH_ID)

        assert len(match_heroes) == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_heroes_in_match_returns_expected_heroes(self, heroes_resource):
        """Test that get_heroes_in_match returns the exact expected heroes."""
        match_heroes = await heroes_resource.get_heroes_in_match(self.REAL_MATCH_ID)

        returned_hero_keys = set(match_heroes.keys())

        assert returned_hero_keys == self.EXPECTED_MATCH_HEROES

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_heroes_in_match_has_full_constants_data(self, heroes_resource):
        """Test that match heroes have full dotaconstants format."""
        match_heroes = await heroes_resource.get_heroes_in_match(self.REAL_MATCH_ID)

        for hero_key, hero_data in match_heroes.items():
            assert "id" in hero_data
            assert "name" in hero_data
            assert "localized_name" in hero_data
            assert "primary_attr" in hero_data
            assert "attack_type" in hero_data
            assert "roles" in hero_data

    @pytest.mark.asyncio
    async def test_get_heroes_in_match_with_invalid_match_id(self, heroes_resource):
        """Test error handling with invalid match ID."""
        invalid_match_heroes = await heroes_resource.get_heroes_in_match(999999999)

        assert invalid_match_heroes == {}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_match_heroes_contain_expected_specific_heroes(self, heroes_resource):
        """Test that specific known heroes appear in the match with correct data."""
        match_heroes = await heroes_resource.get_heroes_in_match(self.REAL_MATCH_ID)

        assert "npc_dota_hero_earthshaker" in match_heroes
        earthshaker = match_heroes["npc_dota_hero_earthshaker"]
        assert earthshaker["id"] == 7
        assert earthshaker["localized_name"] == "Earthshaker"
        assert earthshaker["primary_attr"] == "str"

        assert "npc_dota_hero_juggernaut" in match_heroes
        juggernaut = match_heroes["npc_dota_hero_juggernaut"]
        assert juggernaut["id"] == 8
        assert juggernaut["localized_name"] == "Juggernaut"
        assert juggernaut["primary_attr"] == "agi"

        assert "npc_dota_hero_pugna" in match_heroes
        pugna = match_heroes["npc_dota_hero_pugna"]
        assert pugna["id"] == 45
        assert pugna["localized_name"] == "Pugna"
        assert pugna["primary_attr"] == "int"


class TestHeroesResourceErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_resource_handles_missing_constants(self):
        """Test that resource handles missing constants gracefully."""
        from unittest.mock import patch

        resource = HeroesResource()
        with patch.object(resource.constants, 'get_heroes_constants', return_value=None):
            with patch.object(resource.constants, 'fetch_constants_file', side_effect=Exception("Network error")):
                heroes_data = await resource.get_all_heroes()

        assert heroes_data == {}

    @pytest.mark.asyncio
    async def test_get_all_heroes_with_empty_constants(self):
        """Test get_all_heroes behavior with empty constants data."""
        from unittest.mock import patch

        resource = HeroesResource()
        with patch.object(resource.constants, 'get_heroes_constants', return_value=None):
            with patch.object(resource.constants, 'fetch_constants_file', side_effect=Exception("Network error")):
                all_heroes = await resource.get_all_heroes()

        assert all_heroes == {}

    @pytest.mark.asyncio
    async def test_get_heroes_in_match_with_empty_constants(self):
        """Test get_heroes_in_match behavior with empty constants data."""
        from unittest.mock import patch

        resource = HeroesResource()
        with patch.object(resource.constants, 'get_heroes_constants', return_value=None):
            with patch.object(resource.constants, 'enrich_hero_picks', return_value=[]):
                match_heroes = await resource.get_heroes_in_match(123456)

        assert match_heroes == {}
