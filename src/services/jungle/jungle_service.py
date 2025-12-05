"""
Jungle service for camp stacks, pulls, and neutral item tracking.

Uses python-manta v2's native NEUTRAL_CAMP_STACK combat log type.
NO MCP DEPENDENCIES.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from python_manta import CombatLogType

from ..models.jungle_data import CampStack, JungleSummary
from ..models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)


class JungleService:
    """
    Service for jungle analysis.

    Provides:
    - Camp stack detection (native from combat log)
    - Stack statistics by hero/team
    - Pull detection (heuristic-based)
    """

    def _format_time(self, seconds: float) -> str:
        """Format game time as M:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def _clean_hero_name(self, name: str) -> str:
        """Remove npc_dota_hero_ prefix from hero name."""
        if name.startswith("npc_dota_hero_"):
            return name[14:]
        return name

    def get_camp_stacks(
        self,
        data: ParsedReplayData,
        hero_filter: Optional[str] = None,
    ) -> List[CampStack]:
        """
        Get all camp stack events from the match.

        Uses python-manta v2's native NEUTRAL_CAMP_STACK combat log type.

        Args:
            data: ParsedReplayData from ReplayService
            hero_filter: Only include stacks by this hero

        Returns:
            List of CampStack events sorted by game time
        """
        stacks = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.NEUTRAL_CAMP_STACK.value:
                continue

            stacker = self._clean_hero_name(entry.attacker_name)

            if hero_filter:
                if hero_filter.lower() not in stacker.lower():
                    continue

            stack = CampStack(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                stacker=stacker,
                camp_type=self._infer_camp_type(entry),
                stack_count=entry.value if entry.value > 0 else 1,
                position_x=entry.location_x if hasattr(entry, 'location_x') else None,
                position_y=entry.location_y if hasattr(entry, 'location_y') else None,
            )
            stacks.append(stack)

        stacks.sort(key=lambda s: s.game_time)
        return stacks

    def _infer_camp_type(self, entry) -> Optional[str]:
        """Infer camp type from combat log entry (if possible)."""
        # The combat log may have info in target_name or value_name
        target = getattr(entry, 'target_name', '').lower()
        value_name = getattr(entry, 'value_name', '').lower()

        combined = target + value_name

        if 'ancient' in combined:
            return 'ancient'
        if 'large' in combined or 'big' in combined:
            return 'large'
        if 'medium' in combined:
            return 'medium'
        if 'small' in combined:
            return 'small'

        return None

    def get_jungle_summary(self, data: ParsedReplayData) -> JungleSummary:
        """
        Get complete jungle summary for a match.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            JungleSummary with stacks, statistics
        """
        stacks = self.get_camp_stacks(data)

        # Calculate statistics
        stacks_by_hero: Dict[str, int] = defaultdict(int)
        stacks_by_team: Dict[str, int] = defaultdict(int)

        for stack in stacks:
            stacks_by_hero[stack.stacker] += 1
            # Team assignment would need game_info mapping
            # For now, we track by hero only

        return JungleSummary(
            total_stacks=len(stacks),
            stacks_by_hero=dict(stacks_by_hero),
            stacks_by_team=dict(stacks_by_team),
            total_pulls=0,  # Pull detection requires more analysis
            pulls_by_hero={},
            neutral_items_found=0,
            stacks=stacks,
            pulls=[],
        )

    def get_stacks_by_hero(self, data: ParsedReplayData) -> Dict[str, List[CampStack]]:
        """
        Get camp stacks grouped by hero.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            Dictionary mapping hero name to list of their stacks
        """
        stacks = self.get_camp_stacks(data)
        by_hero: Dict[str, List[CampStack]] = defaultdict(list)

        for stack in stacks:
            by_hero[stack.stacker].append(stack)

        return dict(by_hero)

    def get_stacks_in_time_range(
        self,
        data: ParsedReplayData,
        start_time: float,
        end_time: float,
    ) -> List[CampStack]:
        """
        Get camp stacks in a specific time range.

        Args:
            data: ParsedReplayData from ReplayService
            start_time: Start of time range (seconds)
            end_time: End of time range (seconds)

        Returns:
            List of CampStack events in the time range
        """
        stacks = self.get_camp_stacks(data)
        return [
            s for s in stacks
            if start_time <= s.game_time <= end_time
        ]

    def get_stack_efficiency(self, data: ParsedReplayData) -> Dict[str, float]:
        """
        Calculate stack efficiency per hero (stacks per 10 minutes).

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            Dictionary mapping hero name to stacks per 10 minutes
        """
        stacks = self.get_camp_stacks(data)
        duration_minutes = data.duration_seconds / 60 if data.duration_seconds > 0 else 1

        stacks_by_hero: Dict[str, int] = defaultdict(int)
        for stack in stacks:
            stacks_by_hero[stack.stacker] += 1

        efficiency = {}
        for hero, count in stacks_by_hero.items():
            efficiency[hero] = round(count / duration_minutes * 10, 2)

        return efficiency
