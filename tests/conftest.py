"""
Shared pytest fixtures for Dota 2 MCP server tests.

Uses v2 services exclusively. Parses replay data ONCE at session start.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import pytest

from src.models.combat_log import DetailLevel
from src.services.combat.combat_service import CombatService
from src.services.combat.fight_service import FightService
from src.services.models.replay_data import ParsedReplayData
from src.services.replay.replay_service import ReplayService


def _get_replay_dir() -> Path:
    """Get replay directory, checking DOTA_REPLAY_CACHE env var first."""
    if env_cache := os.environ.get("DOTA_REPLAY_CACHE"):
        return Path(env_cache).expanduser()
    return Path.home() / "dota2" / "replays"


# Test match ID with known verified data
TEST_MATCH_ID = 8461956309
REPLAY_PATH = _get_replay_dir() / f"{TEST_MATCH_ID}.dem"

# Verified data from Dotabuff for match 8461956309
FIRST_BLOOD_TIME = 288.0  # 4:48 in seconds
FIRST_BLOOD_VICTIM = "earthshaker"
FIRST_BLOOD_KILLER = "disruptor"

# Second test match - 8594217096 (OG vs Team - Radiant win)
TEST_MATCH_ID_2 = 8594217096
REPLAY_PATH_2 = _get_replay_dir() / f"{TEST_MATCH_ID_2}.dem"

# Verified data for match 8594217096
MATCH_2_FIRST_BLOOD_TIME = 84.0  # 1:24 in seconds
MATCH_2_FIRST_BLOOD_VICTIM = "batrider"
MATCH_2_FIRST_BLOOD_KILLER = "pugna"
MATCH_2_TOTAL_DEATHS = 53  # After game start
MATCH_2_ROSHAN_KILLS = 3
MATCH_2_TORMENTOR_KILLS = 2
MATCH_2_TOWER_KILLS = 14
MATCH_2_BARRACKS_KILLS = 6
MATCH_2_RUNE_PICKUPS = 13
MATCH_2_COURIER_KILLS = 5


# =============================================================================
# Session-scoped cache - parsed ONCE at test session start
# =============================================================================

_parsed_data: Optional[ParsedReplayData] = None
_parsed_data_2: Optional[ParsedReplayData] = None  # Match 2
_replay_service: Optional[ReplayService] = None
_combat_service: Optional[CombatService] = None
_fight_service: Optional[FightService] = None
_cache = {}


def _clear_in_memory_cache():
    """Clear all in-memory cached data to force re-parsing."""
    global _parsed_data, _parsed_data_2, _replay_service, _cache
    _parsed_data = None
    _parsed_data_2 = None
    _replay_service = None
    _cache = {}


@pytest.fixture(scope="session", autouse=True)
def clear_cache_at_session_start_and_end():
    """Clear in-memory cache at start and end of each test session."""
    _clear_in_memory_cache()
    yield
    _clear_in_memory_cache()


def _get_replay_service() -> ReplayService:
    """Get or create ReplayService singleton."""
    global _replay_service
    if _replay_service is None:
        _replay_service = ReplayService()
    return _replay_service


def _get_parsed_data() -> ParsedReplayData:
    """Get parsed replay data, parsing once if needed."""
    global _parsed_data
    if _parsed_data is not None:
        return _parsed_data

    if not REPLAY_PATH.exists():
        raise FileNotFoundError(f"Replay file not found: {REPLAY_PATH}")

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


def _get_parsed_data_2() -> ParsedReplayData:
    """Get parsed replay data for match 2, parsing once if needed."""
    global _parsed_data_2
    if _parsed_data_2 is not None:
        return _parsed_data_2

    if not REPLAY_PATH_2.exists():
        raise FileNotFoundError(f"Replay file not found: {REPLAY_PATH_2}")

    print(f"\n[conftest] Loading replay {TEST_MATCH_ID_2} via v2 ReplayService...")
    rs = _get_replay_service()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, rs.get_parsed_data(TEST_MATCH_ID_2))
            _parsed_data_2 = future.result()
    else:
        _parsed_data_2 = asyncio.run(rs.get_parsed_data(TEST_MATCH_ID_2))
    print(f"[conftest] Loaded {len(_parsed_data_2.combat_log_entries)} combat log entries for match 2")
    return _parsed_data_2


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

    data = _get_parsed_data()  # Raises FileNotFoundError if not available

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
        raise FileNotFoundError(f"Replay file not found: {REPLAY_PATH}")
    data = _get_parsed_data()
    if data is None:
        raise ValueError("Failed to parse replay")
    return data


# =============================================================================
# Combat Service fixtures
# =============================================================================

def _require_replay():
    """Fail if replay is not available."""
    if not REPLAY_PATH.exists():
        raise FileNotFoundError(f"Replay file not found: {REPLAY_PATH}")


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


# =============================================================================
# Farming Service fixtures
# =============================================================================

_farming_service = None
_lane_service = None


def _get_farming_service():
    """Get or create FarmingService singleton."""
    global _farming_service
    if _farming_service is None:
        from src.services.farming.farming_service import FarmingService
        _farming_service = FarmingService()
    return _farming_service


def _get_lane_service():
    """Get or create LaneService singleton."""
    global _lane_service
    if _lane_service is None:
        from src.services.lane.lane_service import LaneService
        _lane_service = LaneService()
    return _lane_service


@pytest.fixture(scope="session")
def farming_service():
    """FarmingService instance."""
    return _get_farming_service()


@pytest.fixture(scope="session")
def lane_service():
    """LaneService instance."""
    return _get_lane_service()


@pytest.fixture(scope="session")
def medusa_farming_pattern():
    """Farming pattern for Medusa (0-15 min) from match 8461956309."""
    _require_replay()
    _ensure_parsed()
    cache_key = "medusa_farming_0_15"
    if cache_key not in _cache:
        data = _get_parsed_data()
        fs = _get_farming_service()
        _cache[cache_key] = fs.get_farming_pattern(
            data, "medusa", start_minute=0, end_minute=15, item_timings=[]
        )
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def juggernaut_farming_pattern():
    """Farming pattern for Juggernaut (0-15 min) from match 8461956309."""
    _require_replay()
    _ensure_parsed()
    cache_key = "juggernaut_farming_0_15"
    if cache_key not in _cache:
        data = _get_parsed_data()
        fs = _get_farming_service()
        _cache[cache_key] = fs.get_farming_pattern(
            data, "juggernaut", start_minute=0, end_minute=15, item_timings=[]
        )
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def lane_summary():
    """Lane summary for match 8461956309."""
    _require_replay()
    _ensure_parsed()
    cache_key = "lane_summary"
    if cache_key not in _cache:
        data = _get_parsed_data()
        ls = _get_lane_service()
        _cache[cache_key] = ls.get_lane_summary(data)
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def cs_at_10_minutes():
    """CS data at 10 minutes for match 8461956309."""
    _require_replay()
    _ensure_parsed()
    cache_key = "cs_at_10"
    if cache_key not in _cache:
        data = _get_parsed_data()
        ls = _get_lane_service()
        _cache[cache_key] = ls.get_cs_at_minute(data, 10)
    return _cache.get(cache_key)


# =============================================================================
# Match Fetcher fixtures (OpenDota API data)
# =============================================================================

_match_fetcher = None
_match_players_cache = None


def _get_match_fetcher():
    """Get or create MatchFetcher singleton."""
    global _match_fetcher
    if _match_fetcher is None:
        from src.utils.match_fetcher import MatchFetcher
        _match_fetcher = MatchFetcher()
    return _match_fetcher


@pytest.fixture(scope="session")
def match_players():
    """Player data from OpenDota for match 8461956309."""
    global _match_players_cache
    if _match_players_cache is None:
        mf = _get_match_fetcher()
        _match_players_cache = asyncio.run(mf.get_players(TEST_MATCH_ID))
    return _match_players_cache


# =============================================================================
# Match 2 fixtures (8594217096) - OG match with Pure, bzm, 33, Whitemon, Ari
# =============================================================================

_match_2_players_cache = None


def _require_replay_2():
    """Fail if replay 2 is not available."""
    if not REPLAY_PATH_2.exists():
        raise FileNotFoundError(f"Replay file not found: {REPLAY_PATH_2}")


@pytest.fixture(scope="session")
def parsed_replay_data_2():
    """Parsed replay data for match 8594217096."""
    return _get_parsed_data_2()  # Raises FileNotFoundError if not available


@pytest.fixture(scope="session")
def hero_deaths_2(parsed_replay_data_2):
    """Hero deaths from match 8594217096."""
    cs = _get_combat_service()
    deaths = cs.get_hero_deaths(parsed_replay_data_2)
    # Filter to game deaths only (after 0:00)
    return [d for d in deaths if d.game_time > 0]


@pytest.fixture(scope="session")
def roshan_kills_2(parsed_replay_data_2):
    """Roshan kills from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_roshan_kills(parsed_replay_data_2)


@pytest.fixture(scope="session")
def tormentor_kills_2(parsed_replay_data_2):
    """Tormentor kills from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_tormentor_kills(parsed_replay_data_2)


@pytest.fixture(scope="session")
def tower_kills_2(parsed_replay_data_2):
    """Tower kills from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_tower_kills(parsed_replay_data_2)


@pytest.fixture(scope="session")
def barracks_kills_2(parsed_replay_data_2):
    """Barracks kills from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_barracks_kills(parsed_replay_data_2)


@pytest.fixture(scope="session")
def rune_pickups_2(parsed_replay_data_2):
    """Rune pickups from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_rune_pickups(parsed_replay_data_2)


@pytest.fixture(scope="session")
def courier_kills_2(parsed_replay_data_2):
    """Courier kills from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_courier_kills(parsed_replay_data_2)


@pytest.fixture(scope="session")
def match_players_2():
    """Player data from OpenDota for match 8594217096."""
    global _match_2_players_cache
    if _match_2_players_cache is None:
        mf = _get_match_fetcher()
        _match_2_players_cache = asyncio.run(mf.get_players(TEST_MATCH_ID_2))
    return _match_2_players_cache


@pytest.fixture(scope="session")
def lane_summary_2(parsed_replay_data_2):
    """Lane summary for match 8594217096."""
    ls = _get_lane_service()
    return ls.get_lane_summary(parsed_replay_data_2)


@pytest.fixture(scope="session")
def all_fights_2(parsed_replay_data_2):
    """All fights from match 8594217096."""
    fs = _get_fight_service()
    return fs.get_all_fights(parsed_replay_data_2)


@pytest.fixture(scope="session")
def combat_log_1800_1900_2(parsed_replay_data_2):
    """Combat log 30:00-31:40 from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_combat_log(parsed_replay_data_2, start_time=1800, end_time=1900)


@pytest.fixture(scope="session")
def combat_log_narrative_2(parsed_replay_data_2):
    """Combat log 30:00-31:40 NARRATIVE from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_combat_log(
        parsed_replay_data_2, start_time=1800, end_time=1900,
        detail_level=DetailLevel.NARRATIVE
    )


@pytest.fixture(scope="session")
def combat_log_tactical_2(parsed_replay_data_2):
    """Combat log 30:00-31:40 TACTICAL from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_combat_log(
        parsed_replay_data_2, start_time=1800, end_time=1900,
        detail_level=DetailLevel.TACTICAL
    )


@pytest.fixture(scope="session")
def combat_log_full_2(parsed_replay_data_2):
    """Combat log 30:00-31:40 FULL from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_combat_log(
        parsed_replay_data_2, start_time=1800, end_time=1900,
        detail_level=DetailLevel.FULL
    )


@pytest.fixture(scope="session")
def combat_log_juggernaut_2(parsed_replay_data_2):
    """Combat log filtered to Juggernaut from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_combat_log(
        parsed_replay_data_2, start_time=1800, end_time=1900,
        hero_filter="juggernaut"
    )


@pytest.fixture(scope="session")
def item_purchases_2(parsed_replay_data_2):
    """Item purchases from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_item_purchases(parsed_replay_data_2)


@pytest.fixture(scope="session")
def item_purchases_juggernaut_2(parsed_replay_data_2):
    """Item purchases for Juggernaut from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_item_purchases(parsed_replay_data_2, hero_filter="juggernaut")


@pytest.fixture(scope="session")
def juggernaut_farming_2(parsed_replay_data_2):
    """Farming pattern for Juggernaut (0-15 min) from match 8594217096."""
    fs = _get_farming_service()
    return fs.get_farming_pattern(
        parsed_replay_data_2, "juggernaut", start_minute=0, end_minute=15, item_timings=[]
    )


@pytest.fixture(scope="session")
def void_spirit_farming_2(parsed_replay_data_2):
    """Farming pattern for Void Spirit (0-15 min) from match 8594217096."""
    fs = _get_farming_service()
    return fs.get_farming_pattern(
        parsed_replay_data_2, "void_spirit", start_minute=0, end_minute=15, item_timings=[]
    )


@pytest.fixture(scope="session")
def cs_at_10_2(parsed_replay_data_2):
    """CS data at 10 minutes for match 8594217096."""
    ls = _get_lane_service()
    return ls.get_cs_at_minute(parsed_replay_data_2, 10)


@pytest.fixture(scope="session")
def hero_combat_analysis_juggernaut_2(parsed_replay_data_2, all_fights_2):
    """Hero combat analysis for Juggernaut from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_hero_combat_analysis(
        parsed_replay_data_2, TEST_MATCH_ID_2, "juggernaut", all_fights_2.fights
    )


@pytest.fixture(scope="session")
def hero_combat_analysis_centaur_2(parsed_replay_data_2, all_fights_2):
    """Hero combat analysis for Centaur from match 8594217096."""
    cs = _get_combat_service()
    return cs.get_hero_combat_analysis(
        parsed_replay_data_2, TEST_MATCH_ID_2, "centaur", all_fights_2.fights
    )


# =============================================================================
# Pro Scene fixtures (real data from OpenDota)
# =============================================================================

@pytest.fixture(scope="session")
def pro_players_data():
    """Real pro player data from OpenDota."""
    cache_key = "pro_players"
    if cache_key not in _cache:
        from src.utils.pro_scene_fetcher import pro_scene_fetcher
        _cache[cache_key] = asyncio.run(pro_scene_fetcher.fetch_pro_players())
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def pro_teams_data():
    """Real pro team data from OpenDota."""
    cache_key = "pro_teams"
    if cache_key not in _cache:
        from src.utils.pro_scene_fetcher import pro_scene_fetcher
        _cache[cache_key] = asyncio.run(pro_scene_fetcher.fetch_teams())
    return _cache.get(cache_key)


@pytest.fixture(scope="session")
def pro_matches_data():
    """Real pro match data from OpenDota."""
    cache_key = "pro_matches"
    if cache_key not in _cache:
        from opendota import OpenDota

        async def fetch():
            async with OpenDota() as client:
                return await client.get_pro_matches()

        _cache[cache_key] = asyncio.run(fetch())
    return _cache.get(cache_key)
