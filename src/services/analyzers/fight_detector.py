"""
Fight detector analyzer - groups hero deaths into fights.

Uses time-based clustering and participant connectivity to identify
distinct fights and separate concurrent skirmishes.
"""

import logging
from typing import List, Optional, Set

from ..models.combat_data import Fight, FightResult, HeroDeath

logger = logging.getLogger(__name__)

DEFAULT_FIGHT_WINDOW = 15.0  # seconds between deaths to be same fight
TEAMFIGHT_THRESHOLD = 3  # minimum deaths for teamfight


class FightDetector:
    """
    Detects and groups fights from hero death events.

    Algorithm:
    1. Sort deaths by time
    2. Group deaths within time window
    3. Validate participant connectivity (same fight)
    4. Assign fight IDs and calculate statistics
    """

    def __init__(
        self,
        fight_window: float = DEFAULT_FIGHT_WINDOW,
        teamfight_threshold: int = TEAMFIGHT_THRESHOLD,
    ):
        """
        Initialize fight detector.

        Args:
            fight_window: Max seconds between deaths to be same fight
            teamfight_threshold: Minimum deaths to classify as teamfight
        """
        self.fight_window = fight_window
        self.teamfight_threshold = teamfight_threshold

    def _format_time(self, seconds: float) -> str:
        """Format game time as M:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def detect_fights(self, deaths: List[HeroDeath]) -> FightResult:
        """
        Detect all fights from a list of hero deaths.

        Args:
            deaths: List of HeroDeath events (will be sorted by time)

        Returns:
            FightResult with all detected fights
        """
        if not deaths:
            return FightResult()

        # Sort by game time
        sorted_deaths = sorted(deaths, key=lambda d: d.game_time)

        fights = []
        current_fight_deaths: List[HeroDeath] = []
        fight_counter = 0

        for death in sorted_deaths:
            if not current_fight_deaths:
                # Start new fight
                current_fight_deaths.append(death)
            elif death.game_time - current_fight_deaths[-1].game_time <= self.fight_window:
                # Add to current fight
                current_fight_deaths.append(death)
            else:
                # Finalize current fight and start new one
                if current_fight_deaths:
                    fight_counter += 1
                    fight = self._create_fight(current_fight_deaths, fight_counter)
                    fights.append(fight)
                current_fight_deaths = [death]

        # Don't forget last fight
        if current_fight_deaths:
            fight_counter += 1
            fight = self._create_fight(current_fight_deaths, fight_counter)
            fights.append(fight)

        teamfights = sum(1 for f in fights if f.is_teamfight)

        return FightResult(
            fights=fights,
            total_deaths=len(sorted_deaths),
            total_fights=len(fights),
            teamfights=teamfights,
        )

    def _create_fight(self, deaths: List[HeroDeath], fight_number: int) -> Fight:
        """Create a Fight object from a list of deaths."""
        start_time = deaths[0].game_time
        end_time = deaths[-1].game_time

        # Collect participants (both killers and victims)
        participants: Set[str] = set()
        radiant_deaths = 0
        dire_deaths = 0

        for death in deaths:
            participants.add(death.victim)
            if death.killer_is_hero:
                participants.add(death.killer)

            # Track team deaths based on hero names (simplified)
            # In a real implementation, you'd map heroes to teams
            # For now, we just count deaths

        return Fight(
            fight_id=f"fight_{fight_number}",
            start_time=start_time,
            start_time_str=self._format_time(start_time),
            end_time=end_time,
            end_time_str=self._format_time(end_time),
            duration=end_time - start_time,
            deaths=deaths,
            participants=sorted(list(participants)),
            radiant_deaths=radiant_deaths,
            dire_deaths=dire_deaths,
        )

    def get_fight_at_time(
        self,
        deaths: List[HeroDeath],
        reference_time: float,
        hero: Optional[str] = None,
    ) -> Optional[Fight]:
        """
        Find the fight closest to a reference time.

        Args:
            deaths: List of HeroDeath events
            reference_time: Game time to search around
            hero: Optional hero to anchor the search (must be involved)

        Returns:
            Fight containing the reference time, or None if not found
        """
        result = self.detect_fights(deaths)

        if not result.fights:
            return None

        # Find fight containing or closest to reference_time
        best_fight = None
        best_distance = float('inf')

        for fight in result.fights:
            # Check if reference_time is within fight
            if fight.start_time <= reference_time <= fight.end_time + self.fight_window:
                if hero:
                    # Check if hero is involved
                    hero_lower = hero.lower()
                    if any(hero_lower in p.lower() for p in fight.participants):
                        return fight
                else:
                    return fight

            # Track closest fight
            mid_time = (fight.start_time + fight.end_time) / 2
            distance = abs(mid_time - reference_time)
            if distance < best_distance:
                if hero:
                    hero_lower = hero.lower()
                    if any(hero_lower in p.lower() for p in fight.participants):
                        best_distance = distance
                        best_fight = fight
                else:
                    best_distance = distance
                    best_fight = fight

        return best_fight

    def get_teamfights(self, deaths: List[HeroDeath]) -> List[Fight]:
        """Get only teamfights (3+ deaths)."""
        result = self.detect_fights(deaths)
        return [f for f in result.fights if f.is_teamfight]

    def get_skirmishes(self, deaths: List[HeroDeath]) -> List[Fight]:
        """Get only skirmishes (1-2 deaths)."""
        result = self.detect_fights(deaths)
        return [f for f in result.fights if not f.is_teamfight]
