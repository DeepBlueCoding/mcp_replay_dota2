"""
Lane service for laning phase analysis.

Uses entity snapshots to track hero positions, CS, and lane equilibrium.
NO MCP DEPENDENCIES.
"""

import logging
from typing import Dict, List, Optional

from ..models.lane_data import HeroLaneStats, HeroPosition, LaneSummary
from ..models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)

# Map coordinate boundaries for lane classification
# Dota 2 map is roughly -8000 to +8000
LANE_BOUNDARIES = {
    # Top lane (Dire safelane, Radiant offlane)
    "top": {"x_min": -7000, "x_max": 0, "y_min": 2000, "y_max": 8000},
    # Mid lane
    "mid": {"x_min": -3000, "x_max": 3000, "y_min": -3000, "y_max": 3000},
    # Bot lane (Radiant safelane, Dire offlane)
    "bot": {"x_min": 0, "x_max": 7000, "y_min": -8000, "y_max": -2000},
}

# Laning phase typically ends around 10-12 minutes
LANING_PHASE_END = 600  # 10 minutes in seconds


class LaneService:
    """
    Service for lane analysis.

    Provides:
    - Hero positions during laning phase
    - CS tracking at minute intervals
    - Lane equilibrium analysis
    - Lane winner detection
    """

    def _format_time(self, seconds: float) -> str:
        """Format game time as M:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def _clean_hero_name(self, name: str) -> str:
        """Remove npc_dota_hero_ prefix."""
        if name and name.startswith("npc_dota_hero_"):
            return name[14:]
        return name or ""

    def _classify_lane(self, x: float, y: float) -> Optional[str]:
        """Classify position to a lane."""
        for lane, bounds in LANE_BOUNDARIES.items():
            if (bounds["x_min"] <= x <= bounds["x_max"] and
                bounds["y_min"] <= y <= bounds["y_max"]):
                return lane
        return None  # Jungle or other area

    def get_hero_positions_at_minute(
        self,
        data: ParsedReplayData,
        minute: int,
    ) -> List[HeroPosition]:
        """
        Get hero positions at a specific minute.

        Args:
            data: ParsedReplayData from ReplayService
            minute: Game minute to query

        Returns:
            List of HeroPosition for all heroes
        """
        target_time = minute * 60
        positions = []

        # Find closest entity snapshot to target time
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot:
            return positions

        for hero_snap in best_snapshot.heroes:
            hero_name = self._clean_hero_name(hero_snap.hero_name)
            if not hero_name:
                continue

            # Determine team from player_id (0-4 = Radiant, 5-9 = Dire)
            team = 'radiant' if hero_snap.player_id < 5 else 'dire'

            pos = HeroPosition(
                game_time=best_snapshot.game_time,
                tick=best_snapshot.tick,
                hero=hero_name,
                x=hero_snap.x,
                y=hero_snap.y,
                team=team,
            )
            positions.append(pos)

        return positions

    def get_cs_at_minute(
        self,
        data: ParsedReplayData,
        minute: int,
    ) -> Dict[str, Dict[str, int]]:
        """
        Get last hits and denies for all heroes at a specific minute.

        Args:
            data: ParsedReplayData from ReplayService
            minute: Game minute to query

        Returns:
            Dictionary mapping hero name to {last_hits, denies, gold, level}
        """
        target_time = minute * 60
        cs_data = {}

        # Find closest entity snapshot
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot:
            return cs_data

        for hero_snap in best_snapshot.heroes:
            hero_name = self._clean_hero_name(hero_snap.hero_name)
            if not hero_name:
                continue

            cs_data[hero_name] = {
                'last_hits': hero_snap.last_hits,
                'denies': hero_snap.denies,
                'gold': hero_snap.gold,
                'level': hero_snap.level,
            }

        return cs_data

    def get_lane_summary(self, data: ParsedReplayData) -> LaneSummary:
        """
        Get complete laning phase summary.

        Args:
            data: ParsedReplayData from ReplayService

        Returns:
            LaneSummary with lane winners and hero stats
        """
        # Get CS at 5 and 10 minutes
        cs_5min = self.get_cs_at_minute(data, 5)
        cs_10min = self.get_cs_at_minute(data, 10)

        # Get positions at 5 minutes to determine lanes
        positions_5min = self.get_hero_positions_at_minute(data, 5)

        # Build hero stats
        hero_stats = []
        for pos in positions_5min:
            lane = self._classify_lane(pos.x, pos.y)
            if not lane:
                lane = "jungle"

            # Determine role (simplified - based on lane)
            if pos.team == 'radiant':
                if lane == 'bot':
                    role = 'core'  # Radiant safelane
                elif lane == 'top':
                    role = 'offlane'
                else:
                    role = 'mid' if lane == 'mid' else 'roaming'
            else:
                if lane == 'top':
                    role = 'core'  # Dire safelane
                elif lane == 'bot':
                    role = 'offlane'
                else:
                    role = 'mid' if lane == 'mid' else 'roaming'

            stats_5 = cs_5min.get(pos.hero, {})
            stats_10 = cs_10min.get(pos.hero, {})

            stats = HeroLaneStats(
                hero=pos.hero,
                lane=lane,
                role=role,
                team=pos.team,
                last_hits_5min=stats_5.get('last_hits', 0),
                last_hits_10min=stats_10.get('last_hits', 0),
                denies_5min=stats_5.get('denies', 0),
                denies_10min=stats_10.get('denies', 0),
                gold_5min=stats_5.get('gold', 0),
                gold_10min=stats_10.get('gold', 0),
                level_5min=stats_5.get('level', 1),
                level_10min=stats_10.get('level', 1),
            )
            hero_stats.append(stats)

        # Determine lane winners based on CS at 10min
        lane_winners = self._determine_lane_winners(hero_stats)

        # Calculate overall laning scores
        radiant_score = sum(
            s.last_hits_10min + s.denies_10min * 0.5
            for s in hero_stats if s.team == 'radiant'
        )
        dire_score = sum(
            s.last_hits_10min + s.denies_10min * 0.5
            for s in hero_stats if s.team == 'dire'
        )

        return LaneSummary(
            top_winner=lane_winners.get('top'),
            mid_winner=lane_winners.get('mid'),
            bot_winner=lane_winners.get('bot'),
            radiant_laning_score=radiant_score,
            dire_laning_score=dire_score,
            hero_stats=hero_stats,
            lane_timeline=[],
        )

    def _determine_lane_winners(
        self,
        hero_stats: List[HeroLaneStats],
    ) -> Dict[str, str]:
        """Determine winner of each lane based on CS."""
        lane_scores: Dict[str, Dict[str, int]] = {
            'top': {'radiant': 0, 'dire': 0},
            'mid': {'radiant': 0, 'dire': 0},
            'bot': {'radiant': 0, 'dire': 0},
        }

        for stats in hero_stats:
            if stats.lane in lane_scores:
                score = stats.last_hits_10min + stats.denies_10min
                lane_scores[stats.lane][stats.team] += score

        winners = {}
        for lane, scores in lane_scores.items():
            if scores['radiant'] > scores['dire']:
                winners[lane] = 'radiant'
            elif scores['dire'] > scores['radiant']:
                winners[lane] = 'dire'
            else:
                winners[lane] = 'even'

        return winners

    def get_hero_lane_stats(
        self,
        data: ParsedReplayData,
        hero: str,
    ) -> Optional[HeroLaneStats]:
        """
        Get lane stats for a specific hero.

        Args:
            data: ParsedReplayData from ReplayService
            hero: Hero name to query

        Returns:
            HeroLaneStats for the hero, or None if not found
        """
        summary = self.get_lane_summary(data)
        hero_lower = hero.lower()

        for stats in summary.hero_stats:
            if hero_lower in stats.hero.lower():
                return stats

        return None
