"""
Tests for the FarmingService.

Tests creep classification, camp pattern matching, and time formatting.
These are pure unit tests that don't require replay data.
"""

import pytest

from src.services.farming.farming_service import (
    CAMP_TIERS,
    NEUTRAL_CAMP_PATTERNS,
    FarmingService,
)


# Mark all tests in this module as fast (no replay parsing needed)
pytestmark = pytest.mark.fast


class TestCreepClassification:
    """Tests for creep type classification."""

    @pytest.fixture
    def service(self):
        return FarmingService()

    def test_classify_lane_creep_goodguys(self, service):
        """Lane creeps from goodguys (Radiant) are classified as lane."""
        creep_type, camp = service._classify_creep("npc_dota_creep_goodguys_melee")
        assert creep_type == "lane"
        assert camp is None

    def test_classify_lane_creep_badguys(self, service):
        """Lane creeps from badguys (Dire) are classified as lane."""
        creep_type, camp = service._classify_creep("npc_dota_creep_badguys_ranged")
        assert creep_type == "lane"
        assert camp is None

    def test_classify_neutral_satyr(self, service):
        """Satyr neutrals are classified correctly."""
        creep_type, camp = service._classify_creep("npc_dota_neutral_satyr_hellcaller")
        assert creep_type == "neutral"
        assert camp == "large_satyr"

    def test_classify_neutral_centaur(self, service):
        """Centaur neutrals are classified correctly."""
        creep_type, camp = service._classify_creep("npc_dota_neutral_centaur_khan")
        assert creep_type == "neutral"
        assert camp == "large_centaur"

    def test_classify_neutral_kobold(self, service):
        """Kobold neutrals are classified correctly."""
        creep_type, camp = service._classify_creep("npc_dota_neutral_kobold_taskmaster")
        assert creep_type == "neutral"
        assert camp == "small_kobold"

    def test_classify_neutral_ancient(self, service):
        """Ancient neutrals are classified correctly."""
        creep_type, camp = service._classify_creep("npc_dota_neutral_black_dragon")
        assert creep_type == "neutral"
        assert camp == "ancient_black_dragon"

    def test_classify_neutral_unknown(self, service):
        """Unknown neutrals are classified as neutral with unknown camp."""
        creep_type, camp = service._classify_creep("npc_dota_neutral_some_new_creep")
        assert creep_type == "neutral"
        assert camp == "unknown"

    def test_classify_other_ward(self, service):
        """Wards are classified as other."""
        creep_type, camp = service._classify_creep("npc_dota_observer_wards")
        assert creep_type == "other"
        assert camp is None

    def test_classify_other_summon(self, service):
        """Summons are classified as other."""
        creep_type, camp = service._classify_creep("npc_dota_lone_druid_bear")
        assert creep_type == "other"
        assert camp is None

    def test_classify_empty_name(self, service):
        """Empty names are classified as other."""
        creep_type, camp = service._classify_creep("")
        assert creep_type == "other"
        assert camp is None

    def test_classify_none_name(self, service):
        """None names are classified as other."""
        creep_type, camp = service._classify_creep(None)
        assert creep_type == "other"
        assert camp is None


class TestCampTiers:
    """Tests for camp tier classification."""

    @pytest.fixture
    def service(self):
        return FarmingService()

    def test_ancient_tier(self, service):
        """Ancient camps are tier 'ancient'."""
        assert service._get_camp_tier("ancient_black_dragon") == "ancient"
        assert service._get_camp_tier("ancient_granite") == "ancient"

    def test_large_tier(self, service):
        """Large camps are tier 'large'."""
        assert service._get_camp_tier("large_satyr") == "large"
        assert service._get_camp_tier("large_centaur") == "large"

    def test_medium_tier(self, service):
        """Medium camps are tier 'medium'."""
        assert service._get_camp_tier("medium_wolf") == "medium"
        assert service._get_camp_tier("medium_harpy") == "medium"

    def test_small_tier(self, service):
        """Small camps are tier 'small'."""
        assert service._get_camp_tier("small_kobold") == "small"
        assert service._get_camp_tier("small_ghost") == "small"

    def test_unknown_tier(self, service):
        """Unknown camps return None tier."""
        assert service._get_camp_tier("unknown") is None
        assert service._get_camp_tier(None) is None


class TestTimeFormatting:
    """Tests for time formatting."""

    @pytest.fixture
    def service(self):
        return FarmingService()

    def test_format_zero(self, service):
        """Zero seconds formats as 0:00."""
        assert service._format_time(0) == "0:00"

    def test_format_one_minute(self, service):
        """60 seconds formats as 1:00."""
        assert service._format_time(60) == "1:00"

    def test_format_mixed(self, service):
        """Mixed time formats correctly."""
        assert service._format_time(338) == "5:38"
        assert service._format_time(396) == "6:36"
        assert service._format_time(599) == "9:59"


class TestHeroNameCleaning:
    """Tests for hero name cleaning."""

    @pytest.fixture
    def service(self):
        return FarmingService()

    def test_clean_full_name(self, service):
        """Full hero names are cleaned correctly."""
        assert service._clean_hero_name("npc_dota_hero_terrorblade") == "terrorblade"
        assert service._clean_hero_name("npc_dota_hero_antimage") == "antimage"

    def test_clean_short_name(self, service):
        """Short names without prefix are returned as-is."""
        assert service._clean_hero_name("terrorblade") == "terrorblade"

    def test_clean_empty(self, service):
        """Empty names return empty string."""
        assert service._clean_hero_name("") == ""
        assert service._clean_hero_name(None) == ""


class TestNeutralPatternCoverage:
    """Tests to verify neutral camp pattern coverage."""

    def test_all_patterns_have_tiers(self):
        """All neutral patterns should have a tier classification."""
        all_tier_camps = set()
        for camps in CAMP_TIERS.values():
            all_tier_camps.update(camps)

        for camp_type in set(NEUTRAL_CAMP_PATTERNS.values()):
            assert camp_type in all_tier_camps, f"{camp_type} not in any tier"

    def test_common_neutrals_covered(self):
        """Common neutral creep names are in the pattern list."""
        common_neutrals = [
            "satyr_hellcaller",
            "centaur_khan",
            "dark_troll_warlord",
            "hellbear_smasher",
            "wildwing_ripper",
            "alpha_wolf",
            "harpy_stormcrafter",
            "kobold_taskmaster",
            "gnoll_assassin",
            "black_dragon",
            "granite_golem",
        ]
        for neutral in common_neutrals:
            assert any(
                neutral in pattern for pattern in NEUTRAL_CAMP_PATTERNS
            ), f"{neutral} not covered by patterns"
