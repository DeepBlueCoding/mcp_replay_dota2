"""
Fight service - high-level API for fight analysis.

Combines CombatService and FightDetector for convenient fight queries.
Uses combat-intensity based detection to catch fights without deaths.
"""

import logging
from typing import List, Optional, Set

from ...models.combat_log import DetailLevel
from ..analyzers.fight_analyzer import FightAnalyzer
from ..analyzers.fight_detector import FightDetector
from ..models.combat_data import Fight, FightResult, HeroDeath
from ..models.replay_data import ParsedReplayData
from .combat_service import CombatService

logger = logging.getLogger(__name__)


class FightService:
    """
    High-level service for fight analysis.

    Provides:
    - List all fights in a match
    - Get specific fight by ID or time
    - Get teamfights only
    - Get fight context (deaths + damage around a fight)
    """

    def __init__(
        self,
        combat_service: Optional[CombatService] = None,
        fight_detector: Optional[FightDetector] = None,
        fight_analyzer: Optional[FightAnalyzer] = None,
    ):
        self._combat = combat_service or CombatService()
        self._detector = fight_detector or FightDetector()
        self._analyzer = fight_analyzer or FightAnalyzer()

    def get_all_fights(self, data: ParsedReplayData) -> FightResult:
        """
        Get all fights in a match (legacy death-based detection).

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            FightResult with all fights, statistics
        """
        deaths = self._combat.get_hero_deaths(data)
        return self._detector.detect_fights(deaths)

    def get_all_fights_from_combat(self, data: ParsedReplayData) -> FightResult:
        """
        Get all fights using combat-intensity based detection.

        This method detects fights based on hero-to-hero combat activity,
        not just deaths. It catches teamfights where teams disengage before
        anyone dies, and properly captures the initiation phase.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            FightResult with detected fights
        """
        # Get all combat events (DAMAGE, ABILITY, ITEM)
        all_events = self._combat.get_combat_log(data, detail_level=DetailLevel.FULL)
        deaths = self._combat.get_hero_deaths(data)
        return self._detector.detect_fights_from_combat(all_events, deaths)

    def get_fight_by_id(
        self,
        data: ParsedReplayData,
        fight_id: str,
    ) -> Optional[Fight]:
        """
        Get a specific fight by ID.

        Args:
            data: ParsedReplayData from ReplayService
            fight_id: Fight ID (e.g., "fight_1")

        Returns:
            Fight if found, None otherwise
        """
        result = self.get_all_fights(data)
        for fight in result.fights:
            if fight.fight_id == fight_id:
                return fight
        return None

    def get_fight_at_time(
        self,
        data: ParsedReplayData,
        reference_time: float,
        hero: Optional[str] = None,
    ) -> Optional[Fight]:
        """
        Get the fight at or near a specific time.

        Args:
            data: ParsedReplayData from ReplayService
            reference_time: Game time in seconds
            hero: Optional hero to anchor (must be involved)

        Returns:
            Fight if found, None otherwise
        """
        deaths = self._combat.get_hero_deaths(data)
        return self._detector.get_fight_at_time(deaths, reference_time, hero)

    def get_teamfights(
        self,
        data: ParsedReplayData,
        min_deaths: int = 3,
    ) -> List[Fight]:
        """
        Get only teamfights (3+ deaths by default).

        Args:
            data: ParsedReplayData from ReplayService
            min_deaths: Minimum deaths to classify as teamfight

        Returns:
            List of teamfights
        """
        result = self.get_all_fights(data)
        return [f for f in result.fights if f.total_deaths >= min_deaths]

    def get_fight_summary(self, data: ParsedReplayData) -> dict:
        """
        Get a summary of all fights in the match.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            Dictionary with fight statistics
        """
        result = self.get_all_fights(data)

        return {
            "total_fights": result.total_fights,
            "teamfights": result.teamfights,
            "skirmishes": result.skirmishes,
            "total_deaths": result.total_deaths,
            "fights": [
                {
                    "fight_id": f.fight_id,
                    "start_time": f.start_time_str,
                    "deaths": f.total_deaths,
                    "participants": f.participants,
                    "is_teamfight": f.is_teamfight,
                }
                for f in result.fights
            ],
        }

    def get_deaths_in_fight(
        self,
        data: ParsedReplayData,
        fight_id: str,
    ) -> List[HeroDeath]:
        """
        Get all deaths in a specific fight.

        Args:
            data: ParsedReplayData from ReplayService
            fight_id: Fight ID

        Returns:
            List of HeroDeath events in the fight
        """
        fight = self.get_fight_by_id(data, fight_id)
        if fight:
            return fight.deaths
        return []

    def get_hero_fights(
        self,
        data: ParsedReplayData,
        hero: str,
    ) -> List[Fight]:
        """
        Get all fights a hero was involved in.

        Args:
            data: ParsedReplayData from ReplayService
            hero: Hero name to search for

        Returns:
            List of fights involving the hero
        """
        result = self.get_all_fights(data)
        hero_lower = hero.lower()

        return [
            f for f in result.fights
            if any(hero_lower in p.lower() for p in f.participants)
        ]

    def _get_team_heroes(self, data: ParsedReplayData) -> tuple:
        """
        Extract radiant and dire hero sets from entity snapshots.

        Returns:
            Tuple of (radiant_heroes: Set[str], dire_heroes: Set[str])
        """
        radiant_heroes: Set[str] = set()
        dire_heroes: Set[str] = set()

        # Find a snapshot after laning phase starts (game_time > 60s)
        # The first snapshot may not have all heroes spawned yet
        for snapshot in data.entity_snapshots:
            if snapshot.game_time < 60:
                continue

            if hasattr(snapshot, 'heroes') and snapshot.heroes:
                for hero_snap in snapshot.heroes:
                    hero_name = hero_snap.hero_name
                    if hero_name and hero_name.startswith("npc_dota_hero_"):
                        clean_name = hero_name[14:]
                        # player_id 0-4 = radiant, 5-9 = dire
                        if hasattr(hero_snap, 'player_id'):
                            if hero_snap.player_id < 5:
                                radiant_heroes.add(clean_name)
                            else:
                                dire_heroes.add(clean_name)

            # Stop once we have all 10 heroes
            if len(radiant_heroes) == 5 and len(dire_heroes) == 5:
                break

        return radiant_heroes, dire_heroes

    def get_fight_combat_log(
        self,
        data: ParsedReplayData,
        reference_time: float,
        hero: Optional[str] = None,
        use_combat_detection: bool = True,
        detail_level: DetailLevel = DetailLevel.NARRATIVE,
        max_events: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get fight boundaries, combat log, and highlights for a fight at a given time.

        Uses combat-intensity based detection by default to properly capture
        fight start (including BKB+Blink initiation) and fights without deaths.

        Args:
            data: ParsedReplayData from ReplayService
            reference_time: Game time to anchor the fight search
            hero: Optional hero name to anchor fight detection
            use_combat_detection: Use combat-based detection (default True)
            detail_level: Controls verbosity of returned events (NARRATIVE, TACTICAL, FULL)
            max_events: Maximum events to return (None = no limit)

        Returns:
            Dictionary with fight info, combat events, and highlights, or None if no fight found
        """
        # Get all combat events for detection (always need full data for detection)
        all_events = self._combat.get_combat_log(
            data, detail_level=DetailLevel.FULL
        )
        deaths = self._combat.get_hero_deaths(data)

        if use_combat_detection:
            # Use combat-intensity based detection
            fight = self._detector.get_fight_at_time_from_combat(
                all_events, deaths, reference_time, hero
            )
        else:
            # Legacy death-based detection
            fight = self.get_fight_at_time(data, reference_time, hero)

        if not fight:
            return None

        # Get events within fight boundaries (with buffer)
        start_time = fight.start_time - 2.0
        end_time = fight.end_time + 2.0

        # Get events for the response using requested detail level
        response_events = self._combat.get_combat_log(
            data,
            start_time=start_time,
            end_time=end_time,
            detail_level=detail_level,
            max_events=max_events,
        )

        # Get ALL events for highlight detection (fight already includes initiation)
        highlight_events = self._combat.get_combat_log(
            data,
            start_time=start_time,
            end_time=end_time,
            detail_level=DetailLevel.FULL,
        )

        # Get team rosters for ace detection
        radiant_heroes, dire_heroes = self._get_team_heroes(data)

        # Analyze fight for highlights
        highlights = self._analyzer.analyze_fight(
            events=highlight_events,
            deaths=fight.deaths,
            radiant_heroes=radiant_heroes,
            dire_heroes=dire_heroes,
        )

        return {
            "fight_id": fight.fight_id,
            "fight_start": fight.start_time,
            "fight_start_str": fight.start_time_str,
            "fight_end": fight.end_time,
            "fight_end_str": fight.end_time_str,
            "duration": fight.duration,
            "participants": fight.participants,
            "deaths": fight.deaths,
            "total_deaths": fight.total_deaths,
            "is_teamfight": fight.is_teamfight,
            "total_events": len(response_events),
            "events": response_events,
            "highlights": highlights,
            "detail_level": detail_level.value,
        }
