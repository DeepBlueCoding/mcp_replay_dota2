"""
Shared pytest fixtures for Dota 2 MCP server tests.

Pre-parses all replay data ONCE at session start to avoid re-parsing in every test.
This reduces test time from ~15-20 minutes to ~2-3 minutes.
"""

from pathlib import Path

import pytest

# Test match ID with known verified data
TEST_MATCH_ID = 8461956309
REPLAY_PATH = Path.home() / "dota2" / "replays" / f"{TEST_MATCH_ID}.dem"

# Verified data from Dotabuff for match 8461956309
FIRST_BLOOD_TIME = 288.0  # 4:48 in seconds
FIRST_BLOOD_VICTIM = "earthshaker"
FIRST_BLOOD_KILLER = "disruptor"


# =============================================================================
# Session-scoped cache - parsed ONCE at test session start
# =============================================================================

_cache = {}


def _ensure_parsed():
    """Parse all data once and cache it."""
    if _cache:
        return  # Already parsed

    if not REPLAY_PATH.exists():
        return  # Replay not available

    print(f"\n[conftest] Pre-parsing replay {TEST_MATCH_ID}...")

    from src.utils.combat_log_parser import CombatLogParser
    from src.utils.match_info_parser import MatchInfoParser
    from src.utils.timeline_parser import TimelineParser

    combat_parser = CombatLogParser()
    match_parser = MatchInfoParser()
    timeline_parser = TimelineParser()

    # Parse all combat log data
    print("[conftest] Parsing hero deaths...")
    _cache["deaths"] = combat_parser.get_hero_deaths(REPLAY_PATH, include_position=False)
    _cache["deaths_with_position"] = combat_parser.get_hero_deaths(REPLAY_PATH, include_position=True)

    print("[conftest] Parsing objectives...")
    _cache["objectives"] = combat_parser.get_objective_kills(REPLAY_PATH)

    print("[conftest] Parsing rune pickups...")
    _cache["rune_pickups"] = combat_parser.get_rune_pickups(REPLAY_PATH)

    print("[conftest] Parsing combat log segments...")
    _cache["combat_log_280_290"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=290
    )
    _cache["combat_log_280_290_es"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=290, hero_filter="earthshaker"
    )
    _cache["combat_log_287_289_es"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=287, end_time=289, hero_filter="earthshaker"
    )
    _cache["combat_log_280_300_ability"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=300, types=[5]
    )
    _cache["combat_log_280_300_es_ability"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=300, types=[5], hero_filter="earthshaker"
    )
    _cache["combat_log_280_282_naga_ability"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=282, types=[5], hero_filter="naga"
    )
    _cache["combat_log_280_290_dmg_mod_death"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=280, end_time=290, types=[0, 2, 4]
    )
    _cache["combat_log_0_600_ability"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=0, end_time=600, types=[5]
    )
    _cache["combat_log_320_370"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=320, end_time=370
    )
    _cache["combat_log_360_370"] = combat_parser.get_combat_log(
        REPLAY_PATH, start_time=360, end_time=370
    )
    _cache["combat_log_trigger_only"] = combat_parser.get_combat_log(
        REPLAY_PATH, types=[13]
    )

    print("[conftest] Parsing fight detections...")
    _cache["fight_first_blood"] = combat_parser.get_combat_timespan(
        REPLAY_PATH, reference_time=FIRST_BLOOD_TIME, hero="earthshaker"
    )
    _cache["fight_first_blood_no_hero"] = combat_parser.get_combat_timespan(
        REPLAY_PATH, reference_time=FIRST_BLOOD_TIME, hero=None
    )
    _cache["fight_pango_nf"] = combat_parser.get_combat_timespan(
        REPLAY_PATH, reference_time=268, hero="pangolier"
    )

    print("[conftest] Parsing match info...")
    _cache["match_info"] = match_parser.get_match_info(REPLAY_PATH)
    _cache["draft"] = match_parser.get_draft(REPLAY_PATH)

    print("[conftest] Parsing timeline...")
    _cache["timeline"] = timeline_parser.parse_timeline(REPLAY_PATH)
    _cache["stats_5min"] = timeline_parser.get_stats_at_minute(_cache["timeline"], 5)
    _cache["stats_10min"] = timeline_parser.get_stats_at_minute(_cache["timeline"], 10)

    print("[conftest] Pre-parsing complete!")


# =============================================================================
# Basic fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_replay_path():
    """Session-scoped fixture for test replay path."""
    return REPLAY_PATH


@pytest.fixture(scope="session")
def test_match_id():
    """Session-scoped fixture for test match ID."""
    return TEST_MATCH_ID


@pytest.fixture(scope="session", autouse=True)
def preparse_replay():
    """Auto-run fixture that pre-parses the replay at session start."""
    _ensure_parsed()


# =============================================================================
# Combat Log Parser fixtures
# =============================================================================

@pytest.fixture(scope="session")
def hero_deaths():
    """Cached hero deaths without position."""
    _ensure_parsed()
    return _cache.get("deaths", [])


@pytest.fixture(scope="session")
def hero_deaths_with_position():
    """Cached hero deaths with position data."""
    _ensure_parsed()
    return _cache.get("deaths_with_position", [])


@pytest.fixture(scope="session")
def objectives():
    """Cached objective kills (roshan, tormentor, towers, barracks)."""
    _ensure_parsed()
    return _cache.get("objectives", ([], [], [], []))


@pytest.fixture(scope="session")
def rune_pickups():
    """Cached rune pickups."""
    _ensure_parsed()
    return _cache.get("rune_pickups", [])


@pytest.fixture(scope="session")
def combat_log_280_290():
    """Combat log from 280-290s (first blood area)."""
    _ensure_parsed()
    return _cache.get("combat_log_280_290", [])


@pytest.fixture(scope="session")
def combat_log_280_290_earthshaker():
    """Combat log 280-290s filtered to earthshaker."""
    _ensure_parsed()
    return _cache.get("combat_log_280_290_es", [])


@pytest.fixture(scope="session")
def combat_log_287_289_earthshaker():
    """Combat log 287-289s filtered to earthshaker."""
    _ensure_parsed()
    return _cache.get("combat_log_287_289_es", [])


@pytest.fixture(scope="session")
def combat_log_280_300_ability():
    """Combat log 280-300s, ABILITY events only."""
    _ensure_parsed()
    return _cache.get("combat_log_280_300_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_300_earthshaker_ability():
    """Combat log 280-300s, ABILITY events, earthshaker filter."""
    _ensure_parsed()
    return _cache.get("combat_log_280_300_es_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_282_naga_ability():
    """Combat log 280-282s, ABILITY events, naga filter."""
    _ensure_parsed()
    return _cache.get("combat_log_280_282_naga_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_290_non_ability():
    """Combat log 280-290s, DAMAGE/MODIFIER_ADD/DEATH only."""
    _ensure_parsed()
    return _cache.get("combat_log_280_290_dmg_mod_death", [])


@pytest.fixture(scope="session")
def combat_log_0_600_ability():
    """Combat log 0-600s, ABILITY events only (full match abilities)."""
    _ensure_parsed()
    return _cache.get("combat_log_0_600_ability", [])


@pytest.fixture(scope="session")
def combat_log_320_370():
    """Combat log 320-370s (ability trigger area)."""
    _ensure_parsed()
    return _cache.get("combat_log_320_370", [])


@pytest.fixture(scope="session")
def combat_log_360_370():
    """Combat log 360-370s."""
    _ensure_parsed()
    return _cache.get("combat_log_360_370", [])


@pytest.fixture(scope="session")
def combat_log_trigger_only():
    """Combat log ABILITY_TRIGGER events only."""
    _ensure_parsed()
    return _cache.get("combat_log_trigger_only", [])


# =============================================================================
# Fight Detection fixtures
# =============================================================================

@pytest.fixture(scope="session")
def fight_first_blood():
    """Fight detection result for first blood (earthshaker anchor)."""
    _ensure_parsed()
    return _cache.get("fight_first_blood")


@pytest.fixture(scope="session")
def fight_first_blood_no_hero():
    """Fight detection for first blood without hero anchor."""
    _ensure_parsed()
    return _cache.get("fight_first_blood_no_hero")


@pytest.fixture(scope="session")
def fight_pango_nevermore():
    """Fight detection for pangolier vs nevermore."""
    _ensure_parsed()
    return _cache.get("fight_pango_nf")


# =============================================================================
# Match Info fixtures
# =============================================================================

@pytest.fixture(scope="session")
def match_info():
    """Cached match info."""
    _ensure_parsed()
    return _cache.get("match_info")


@pytest.fixture(scope="session")
def draft():
    """Cached draft data."""
    _ensure_parsed()
    return _cache.get("draft")


# =============================================================================
# Timeline fixtures
# =============================================================================

@pytest.fixture(scope="session")
def timeline():
    """Cached timeline data."""
    _ensure_parsed()
    return _cache.get("timeline")


@pytest.fixture(scope="session")
def stats_5min():
    """Stats at 5 minute mark."""
    _ensure_parsed()
    return _cache.get("stats_5min")


@pytest.fixture(scope="session")
def stats_10min():
    """Stats at 10 minute mark."""
    _ensure_parsed()
    return _cache.get("stats_10min")


