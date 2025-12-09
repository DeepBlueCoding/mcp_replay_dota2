"""
Shared pytest fixtures for Dota 2 MCP server tests.

Uses v2 services exclusively. Parses replay data ONCE at session start.
"""

import asyncio
from pathlib import Path
from typing import Optional

import pytest

from src.models.combat_log import DetailLevel
from src.services.combat.combat_service import CombatService
from src.services.combat.fight_service import FightService
from src.services.models.replay_data import ParsedReplayData
from src.services.replay.replay_service import ReplayService

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

_parsed_data: Optional[ParsedReplayData] = None
_replay_service: Optional[ReplayService] = None
_combat_service: Optional[CombatService] = None
_fight_service: Optional[FightService] = None
_cache = {}


def _get_replay_service() -> ReplayService:
    """Get or create ReplayService singleton."""
    global _replay_service
    if _replay_service is None:
        _replay_service = ReplayService()
    return _replay_service


def _get_parsed_data() -> Optional[ParsedReplayData]:
    """Get parsed replay data, parsing once if needed."""
    global _parsed_data
    if _parsed_data is not None:
        return _parsed_data

    if not REPLAY_PATH.exists():
        return None

    print(f"\n[conftest] Loading replay {TEST_MATCH_ID} via v2 ReplayService...")
    rs = _get_replay_service()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we're already in an async context, create a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, rs.get_parsed_data(TEST_MATCH_ID))
            _parsed_data = future.result()
    else:
        _parsed_data = asyncio.run(rs.get_parsed_data(TEST_MATCH_ID))
    print(f"[conftest] Loaded {len(_parsed_data.combat_log_entries)} combat log entries")
    return _parsed_data


def _get_combat_service() -> CombatService:
    """Get or create CombatService singleton."""
    global _combat_service
    if _combat_service is None:
        _combat_service = CombatService()
    return _combat_service


def _get_fight_service() -> FightService:
    """Get or create FightService singleton."""
    global _fight_service
    if _fight_service is None:
        _fight_service = FightService()
    return _fight_service


def _ensure_parsed():
    """Parse all data once and cache it using v2 services."""
    if _cache:
        return  # Already parsed

    data = _get_parsed_data()
    if data is None:
        return  # Replay not available

    combat = _get_combat_service()
    fight = _get_fight_service()

    print("[conftest] Extracting data via v2 services...")

    # Hero deaths
    _cache["deaths"] = combat.get_hero_deaths(data)

    # Objectives
    _cache["roshan"] = combat.get_roshan_kills(data)
    _cache["tormentor"] = combat.get_tormentor_kills(data)
    _cache["towers"] = combat.get_tower_kills(data)
    _cache["barracks"] = combat.get_barracks_kills(data)

    # Rune pickups
    _cache["rune_pickups"] = combat.get_rune_pickups(data)

    # Combat log segments
    _cache["combat_log_280_290"] = combat.get_combat_log(
        data, start_time=280, end_time=290
    )
    _cache["combat_log_280_290_es"] = combat.get_combat_log(
        data, start_time=280, end_time=290, hero_filter="earthshaker"
    )
    _cache["combat_log_287_289_es"] = combat.get_combat_log(
        data, start_time=287, end_time=289, hero_filter="earthshaker"
    )
    _cache["combat_log_280_300_ability"] = combat.get_combat_log(
        data, start_time=280, end_time=300, types=[5]
    )
    _cache["combat_log_280_300_es_ability"] = combat.get_combat_log(
        data, start_time=280, end_time=300, types=[5], hero_filter="earthshaker"
    )
    _cache["combat_log_280_282_naga_ability"] = combat.get_combat_log(
        data, start_time=280, end_time=282, types=[5], hero_filter="naga"
    )
    _cache["combat_log_280_290_dmg_mod_death"] = combat.get_combat_log(
        data, start_time=280, end_time=290, types=[0, 2, 4]
    )
    _cache["combat_log_0_600_ability"] = combat.get_combat_log(
        data, start_time=0, end_time=600, types=[5]
    )
    _cache["combat_log_320_370"] = combat.get_combat_log(
        data, start_time=320, end_time=370
    )
    _cache["combat_log_360_370"] = combat.get_combat_log(
        data, start_time=360, end_time=370
    )
    _cache["combat_log_trigger_only"] = combat.get_combat_log(
        data, types=[13]
    )
    _cache["combat_log_280_290_narrative"] = combat.get_combat_log(
        data, start_time=280, end_time=290, detail_level=DetailLevel.NARRATIVE
    )
    _cache["combat_log_280_290_tactical"] = combat.get_combat_log(
        data, start_time=280, end_time=290, detail_level=DetailLevel.TACTICAL
    )
    _cache["combat_log_280_290_full"] = combat.get_combat_log(
        data, start_time=280, end_time=290, detail_level=DetailLevel.FULL
    )
    # Pre-game time filter tests (purchases happen at negative times)
    _cache["combat_log_start_time_0"] = combat.get_combat_log(
        data, start_time=0, end_time=120, detail_level=DetailLevel.NARRATIVE
    )
    _cache["combat_log_start_time_neg90"] = combat.get_combat_log(
        data, start_time=-90, end_time=120, detail_level=DetailLevel.NARRATIVE
    )
    _cache["combat_log_start_time_none"] = combat.get_combat_log(
        data, start_time=None, end_time=120, detail_level=DetailLevel.NARRATIVE
    )

    # Fight detections using FightService
    _cache["fights"] = fight.get_all_fights(data)
    _cache["fight_first_blood"] = fight.get_fight_at_time(
        data, reference_time=FIRST_BLOOD_TIME, hero="earthshaker"
    )
    _cache["fight_first_blood_no_hero"] = fight.get_fight_at_time(
        data, reference_time=FIRST_BLOOD_TIME, hero=None
    )
    _cache["fight_pango_nf"] = fight.get_fight_at_time(
        data, reference_time=268, hero="pangolier"
    )

    print("[conftest] v2 data extraction complete!")


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


@pytest.fixture(scope="session")
def parsed_replay_data():
    """Session-scoped fixture for parsed replay data (v2)."""
    if not REPLAY_PATH.exists():
        pytest.skip("Replay file not available")
    data = _get_parsed_data()
    if data is None:
        pytest.skip("Failed to parse replay")
    return data


# =============================================================================
# Combat Service fixtures
# =============================================================================

def _require_replay():
    """Skip test if replay is not available."""
    if not REPLAY_PATH.exists():
        pytest.skip("Replay file not available (run locally with replay)")


@pytest.fixture(scope="session")
def hero_deaths():
    """Cached hero deaths."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("deaths", [])


@pytest.fixture(scope="session")
def hero_deaths_with_position():
    """Cached hero deaths (same as hero_deaths, positions included in v2)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("deaths", [])


@pytest.fixture(scope="session")
def objectives():
    """Cached objective kills as tuple (roshan, tormentor, towers, barracks)."""
    _require_replay()
    _ensure_parsed()
    return (
        _cache.get("roshan", []),
        _cache.get("tormentor", []),
        _cache.get("towers", []),
        _cache.get("barracks", []),
    )


@pytest.fixture(scope="session")
def rune_pickups():
    """Cached rune pickups."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("rune_pickups", [])


@pytest.fixture(scope="session")
def combat_log_280_290():
    """Combat log from 280-290s (first blood area)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290", [])


@pytest.fixture(scope="session")
def combat_log_280_290_earthshaker():
    """Combat log 280-290s filtered to earthshaker."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290_es", [])


@pytest.fixture(scope="session")
def combat_log_287_289_earthshaker():
    """Combat log 287-289s filtered to earthshaker."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_287_289_es", [])


@pytest.fixture(scope="session")
def combat_log_280_300_ability():
    """Combat log 280-300s, ABILITY events only."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_300_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_300_earthshaker_ability():
    """Combat log 280-300s, ABILITY events, earthshaker filter."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_300_es_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_282_naga_ability():
    """Combat log 280-282s, ABILITY events, naga filter."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_282_naga_ability", [])


@pytest.fixture(scope="session")
def combat_log_280_290_non_ability():
    """Combat log 280-290s, DAMAGE/MODIFIER_ADD/DEATH only."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290_dmg_mod_death", [])


@pytest.fixture(scope="session")
def combat_log_280_290_narrative():
    """Combat log 280-290s with detail_level=NARRATIVE."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290_narrative", [])


@pytest.fixture(scope="session")
def combat_log_280_290_tactical():
    """Combat log 280-290s with detail_level=TACTICAL."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290_tactical", [])


@pytest.fixture(scope="session")
def combat_log_280_290_full():
    """Combat log 280-290s with detail_level=FULL."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_280_290_full", [])


@pytest.fixture(scope="session")
def combat_log_0_600_ability():
    """Combat log 0-600s, ABILITY events only."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_0_600_ability", [])


@pytest.fixture(scope="session")
def combat_log_320_370():
    """Combat log 320-370s."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_320_370", [])


@pytest.fixture(scope="session")
def combat_log_360_370():
    """Combat log 360-370s."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_360_370", [])


@pytest.fixture(scope="session")
def combat_log_trigger_only():
    """Combat log ABILITY_TRIGGER events only."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_trigger_only", [])


@pytest.fixture(scope="session")
def combat_log_start_time_0():
    """Combat log with start_time=0 (excludes pre-game)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_start_time_0", [])


@pytest.fixture(scope="session")
def combat_log_start_time_neg90():
    """Combat log with start_time=-90 (includes pre-game)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_start_time_neg90", [])


@pytest.fixture(scope="session")
def combat_log_start_time_none():
    """Combat log with start_time=None (includes all events)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("combat_log_start_time_none", [])


# =============================================================================
# Fight Detection fixtures
# =============================================================================

@pytest.fixture(scope="session")
def fight_first_blood():
    """Fight detection result for first blood (earthshaker anchor)."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("fight_first_blood")


@pytest.fixture(scope="session")
def fight_first_blood_no_hero():
    """Fight detection for first blood without hero anchor."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("fight_first_blood_no_hero")


@pytest.fixture(scope="session")
def fight_pango_nevermore():
    """Fight detection for pangolier vs nevermore."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("fight_pango_nf")


@pytest.fixture(scope="session")
def all_fights():
    """All fights detected in the match."""
    _require_replay()
    _ensure_parsed()
    return _cache.get("fights")


# =============================================================================
# Fight Analyzer fixtures (46:40 teamfight in TI grand final)
# =============================================================================

@pytest.fixture(scope="session")
def fight_4640_combat_log():
    """Combat log from fight at 46:40 (2780-2820s)."""
    _require_replay()
    _ensure_parsed()
    if "fight_4640_combat_log" not in _cache:
        data = _get_parsed_data()
        combat = _get_combat_service()
        # Get combat log for the 46:40 fight window
        _cache["fight_4640_combat_log"] = combat.get_combat_log(
            data, start_time=2780, end_time=2820, types=[0, 2, 4, 5]
        )
    return _cache.get("fight_4640_combat_log", [])


@pytest.fixture(scope="session")
def fight_4640_deaths():
    """Hero deaths from fight at 46:40."""
    _require_replay()
    _ensure_parsed()
    if "fight_4640_deaths" not in _cache:
        data = _get_parsed_data()
        combat = _get_combat_service()
        all_deaths = combat.get_hero_deaths(data)
        # Filter to deaths in 46:20-47:00 window
        _cache["fight_4640_deaths"] = [
            d for d in all_deaths
            if 2780 <= d.game_time <= 2820
        ]
    return _cache.get("fight_4640_deaths", [])


@pytest.fixture(scope="session")
def team_heroes():
    """Team hero assignments extracted from entity snapshots."""
    _require_replay()
    _ensure_parsed()
    if "team_heroes" not in _cache:
        data = _get_parsed_data()
        fight = _get_fight_service()
        radiant, dire = fight._get_team_heroes(data)
        _cache["team_heroes"] = (radiant, dire)
    return _cache.get("team_heroes", (set(), set()))


# =============================================================================
# Hero Combat Analysis fixtures
# =============================================================================

@pytest.fixture(scope="session")
def hero_combat_analysis_earthshaker():
    """Hero combat analysis for earthshaker."""
    _require_replay()
    _ensure_parsed()
    cache_key = "hero_combat_analysis_earthshaker"
    if cache_key not in _cache:
        data = _get_parsed_data()
        combat = _get_combat_service()
        fight = _get_fight_service()
        fights = fight.get_all_fights(data)
        _cache[cache_key] = combat.get_hero_combat_analysis(
            data, TEST_MATCH_ID, "earthshaker", fights.fights
        )
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def hero_combat_analysis_disruptor():
    """Hero combat analysis for disruptor."""
    _require_replay()
    _ensure_parsed()
    cache_key = "hero_combat_analysis_disruptor"
    if cache_key not in _cache:
        data = _get_parsed_data()
        combat = _get_combat_service()
        fight = _get_fight_service()
        fights = fight.get_all_fights(data)
        _cache[cache_key] = combat.get_hero_combat_analysis(
            data, TEST_MATCH_ID, "disruptor", fights.fights
        )
    return _cache.get(cache_key)
