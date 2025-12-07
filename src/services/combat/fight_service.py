"""
Fight service - high-level API for fight analysis.

Combines CombatService and FightDetector for convenient fight queries.
"""

import logging
from typing import List, Optional

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
    ):
        self._combat = combat_service or CombatService()
        self._detector = fight_detector or FightDetector()

    def get_all_fights(self, data: ParsedReplayData) -> FightResult:
        """
        Get all fights in a match.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            FightResult with all fights, statistics
        """
        deaths = self._combat.get_hero_deaths(data)
        return self._detector.detect_fights(deaths)

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

    def get_fight_combat_log(
        self,
        data: ParsedReplayData,
        reference_time: float,
        hero: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get fight boundaries and combat log for a fight at a given time.

        Args:
            data: ParsedReplayData from ReplayService
            reference_time: Game time to anchor the fight search
            hero: Optional hero name to anchor fight detection

        Returns:
            Dictionary with fight info and combat events, or None if no fight found
        """
        fight = self.get_fight_at_time(data, reference_time, hero)
        if not fight:
            return None

        # Get combat log events within fight boundaries (with 2s buffer)
        start_time = fight.start_time - 2.0
        end_time = fight.end_time + 1.0

        events = self._combat.get_combat_log(
            data,
            start_time=start_time,
            end_time=end_time,
            significant_only=True,
        )

        return {
            "fight_id": fight.fight_id,
            "fight_start": fight.start_time,
            "fight_start_str": fight.start_time_str,
            "fight_end": fight.end_time,
            "fight_end_str": fight.end_time_str,
            "duration": fight.duration,
            "participants": fight.participants,
            "total_events": len(events),
            "events": events,
        }
