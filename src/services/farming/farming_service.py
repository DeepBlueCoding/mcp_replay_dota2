"""
Farming service for analyzing hero farming patterns.

Provides minute-by-minute breakdown of creep kills, neutral camp rotations,
and map movement - answering the question "how did X farm?".

NO MCP DEPENDENCIES.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from python_manta import CombatLogType

from ...utils.position_tracker import classify_map_position
from ..models.farming_data import (
    CreepKill,
    FarmingPatternResponse,
    FarmingSummary,
    FarmingTransitions,
    MinuteFarmingData,
)
from ..models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)


# Neutral creep name patterns and their camp types
NEUTRAL_CAMP_PATTERNS = {
    # Ancient camps
    r"black_dragon": "ancient_black_dragon",
    r"black_drake": "ancient_black_dragon",
    r"granite_golem": "ancient_granite",
    r"rock_golem": "ancient_granite",
    r"thunderhide": "ancient_thunderhide",
    r"rumblehide": "ancient_thunderhide",
    r"prowler": "ancient_prowler",
    # Large camps
    r"satyr_hellcaller": "large_satyr",
    r"satyr_soulstealer": "large_satyr",
    r"satyr_trickster": "large_satyr",
    r"centaur_khan": "large_centaur",
    r"centaur_outrunner": "large_centaur",
    r"dark_troll_warlord": "large_troll",
    r"dark_troll": "large_troll",
    r"mud_golem": "large_golem",
    r"shard_golem": "large_golem",
    r"hellbear_smasher": "large_hellbear",
    r"hellbear": "large_hellbear",
    r"wildwing_ripper": "large_wildwing",
    r"wildwing": "large_wildwing",
    # Medium camps
    r"alpha_wolf": "medium_wolf",
    r"giant_wolf": "medium_wolf",
    r"ogre_mauler": "medium_ogre",
    r"ogre_bruiser": "medium_ogre",
    r"polar_furbolg_ursa_warrior": "medium_furbolg",
    r"polar_furbolg": "medium_furbolg",
    r"centaur_courser": "medium_centaur",
    r"warpine_raider": "medium_warpine",
    r"harpy_scout": "medium_harpy",
    r"harpy_stormcrafter": "medium_harpy",
    # Small camps
    r"kobold_taskmaster": "small_kobold",
    r"kobold_tunneler": "small_kobold",
    r"kobold": "small_kobold",
    r"hill_troll_berserker": "small_troll",
    r"hill_troll": "small_troll",
    r"ghost": "small_ghost",
    r"fel_beast": "small_ghost",
    r"vhoul_assassin": "small_vhoul",
    r"gnoll_assassin": "small_gnoll",
}

# Camp tier classification
CAMP_TIERS = {
    "ancient": ["ancient_black_dragon", "ancient_granite", "ancient_thunderhide", "ancient_prowler"],
    "large": ["large_satyr", "large_centaur", "large_troll", "large_golem", "large_hellbear", "large_wildwing"],
    "medium": ["medium_wolf", "medium_ogre", "medium_furbolg", "medium_centaur", "medium_warpine", "medium_harpy"],
    "small": ["small_kobold", "small_troll", "small_ghost", "small_vhoul", "small_gnoll"],
}


class FarmingService:
    """
    Service for farming pattern analysis.

    Provides:
    - Creep kill classification (lane vs neutral)
    - Neutral camp identification
    - Minute-by-minute farming breakdown
    - Farming transition detection
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

    def _is_hero(self, name: str) -> bool:
        """Check if a name is a hero."""
        return "npc_dota_hero_" in name if name else False

    def _classify_creep(self, target_name: str) -> Tuple[str, Optional[str]]:
        """
        Classify a creep by its name.

        Returns:
            Tuple of (creep_type, neutral_camp_type)
            creep_type is 'lane', 'neutral', or 'other'
            neutral_camp_type is the specific camp type or None
        """
        if not target_name:
            return ("other", None)

        target_lower = target_name.lower()

        # Lane creeps
        if "npc_dota_creep_goodguys" in target_lower or "npc_dota_creep_badguys" in target_lower:
            return ("lane", None)

        # Neutral creeps
        if "npc_dota_neutral" in target_lower:
            # Try to identify specific camp type
            for pattern, camp_type in NEUTRAL_CAMP_PATTERNS.items():
                if pattern in target_lower:
                    return ("neutral", camp_type)
            # Generic neutral
            return ("neutral", "unknown")

        # Other (wards, summons, etc.)
        return ("other", None)

    def _get_camp_tier(self, camp_type: Optional[str]) -> Optional[str]:
        """Get the tier (ancient/large/medium/small) of a camp type."""
        if not camp_type:
            return None
        for tier, camps in CAMP_TIERS.items():
            if camp_type in camps:
                return tier
        return None

    def _get_creep_kills(
        self,
        data: ParsedReplayData,
        hero: str,
        start_time: float,
        end_time: float,
    ) -> List[CreepKill]:
        """
        Get all creep kills by a hero in a time range.

        Args:
            data: ParsedReplayData
            hero: Hero name (cleaned, e.g., 'terrorblade')
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            List of CreepKill events sorted by game time
        """
        kills = []
        hero_lower = hero.lower()

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            if entry.game_time < start_time or entry.game_time > end_time:
                continue

            # Check if this hero killed the creep
            attacker_name = self._clean_hero_name(entry.attacker_name)
            if hero_lower not in attacker_name.lower():
                continue

            # Skip hero deaths
            if self._is_hero(entry.target_name):
                continue

            # Classify the creep
            creep_type, neutral_camp = self._classify_creep(entry.target_name)
            if creep_type == "other":
                continue  # Skip summons, wards, etc.

            kills.append(CreepKill(
                game_time=round(entry.game_time, 1),
                game_time_str=self._format_time(entry.game_time),
                creep_name=entry.target_name,
                creep_type=creep_type,
                neutral_camp=neutral_camp,
            ))

        return sorted(kills, key=lambda k: k.game_time)

    def _get_position_at_time(
        self,
        data: ParsedReplayData,
        hero: str,
        target_time: float,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Get hero position at a specific time.

        Returns:
            Tuple of (x, y, map_area) or (None, None, None) if not found
        """
        hero_lower = hero.lower()
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot:
            return (None, None, None)

        for player in best_snapshot.players:
            player_hero = self._clean_hero_name(player.hero_name)
            if hero_lower in player_hero.lower():
                pos = classify_map_position(player.position_x, player.position_y)
                return (player.position_x, player.position_y, pos.region)

        return (None, None, None)

    def _get_stats_at_time(
        self,
        data: ParsedReplayData,
        hero: str,
        target_time: float,
    ) -> Dict[str, int]:
        """
        Get hero stats at a specific time.

        Returns:
            Dict with gold, last_hits, denies, level
        """
        hero_lower = hero.lower()
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot:
            return {"gold": 0, "last_hits": 0, "denies": 0, "level": 1}

        for player in best_snapshot.players:
            player_hero = self._clean_hero_name(player.hero_name)
            if hero_lower in player_hero.lower():
                return {
                    "gold": player.gold,
                    "last_hits": player.last_hits,
                    "denies": player.denies,
                    "level": player.level,
                }

        return {"gold": 0, "last_hits": 0, "denies": 0, "level": 1}

    def _detect_transitions(
        self,
        creep_kills: List[CreepKill],
        minute_data: List[MinuteFarmingData],
    ) -> FarmingTransitions:
        """
        Detect key farming transitions.

        Args:
            creep_kills: All creep kills
            minute_data: Minute-by-minute data

        Returns:
            FarmingTransitions with detected transition points
        """
        transitions = FarmingTransitions()

        # Find first jungle kill
        for kill in creep_kills:
            if kill.creep_type == "neutral":
                transitions.first_jungle_kill_time = kill.game_time
                transitions.first_jungle_kill_str = kill.game_time_str
                break

        # Find first large/ancient camp kill
        for kill in creep_kills:
            if kill.creep_type == "neutral" and kill.neutral_camp:
                tier = self._get_camp_tier(kill.neutral_camp)
                if tier in ("large", "ancient"):
                    transitions.first_large_camp_time = kill.game_time
                    transitions.first_large_camp_str = kill.game_time_str
                    break

        # Detect when hero left lane for jungle rotation pattern
        # Look for first minute where jungle kills >= lane kills and map_area is jungle
        for m in minute_data:
            if m.neutral_creeps_killed >= m.lane_creeps_killed and m.neutral_creeps_killed > 0:
                if m.map_area and "jungle" in m.map_area:
                    transitions.left_lane_time = float(m.minute * 60)
                    transitions.left_lane_str = f"{m.minute}:00"
                    break

        return transitions

    def get_farming_pattern(
        self,
        data: ParsedReplayData,
        hero: str,
        start_minute: int = 0,
        end_minute: int = 10,
    ) -> FarmingPatternResponse:
        """
        Analyze a hero's farming pattern.

        Args:
            data: ParsedReplayData from ReplayService
            hero: Hero name to analyze (fuzzy match supported)
            start_minute: Start of analysis range (default: 0)
            end_minute: End of analysis range (default: 10)

        Returns:
            FarmingPatternResponse with complete farming analysis
        """
        start_time = start_minute * 60.0
        end_time = end_minute * 60.0

        # Get all creep kills in time range
        creep_kills = self._get_creep_kills(data, hero, start_time, end_time)

        # Build minute-by-minute data
        minute_data: List[MinuteFarmingData] = []
        all_camps: Dict[str, int] = defaultdict(int)

        for minute in range(start_minute, end_minute + 1):
            minute_start = minute * 60.0
            minute_end = (minute + 1) * 60.0

            # Count kills in this minute
            lane_kills = 0
            neutral_kills = 0
            camps_this_minute: Dict[str, int] = defaultdict(int)

            for kill in creep_kills:
                if minute_start <= kill.game_time < minute_end:
                    if kill.creep_type == "lane":
                        lane_kills += 1
                    elif kill.creep_type == "neutral":
                        neutral_kills += 1
                        if kill.neutral_camp:
                            # Extract readable camp name
                            camp_name = kill.neutral_camp.replace("_", " ")
                            camps_this_minute[camp_name] += 1
                            all_camps[camp_name] += 1

            # Get position at minute mark
            x, y, area = self._get_position_at_time(data, hero, float(minute * 60))

            # Get stats at minute mark
            stats = self._get_stats_at_time(data, hero, float(minute * 60))

            minute_data.append(MinuteFarmingData(
                minute=minute,
                lane_creeps_killed=lane_kills,
                neutral_creeps_killed=neutral_kills,
                neutral_camps_detail=dict(camps_this_minute),
                position_x=round(x, 1) if x else None,
                position_y=round(y, 1) if y else None,
                map_area=area,
                gold=stats["gold"],
                last_hits=stats["last_hits"],
                denies=stats["denies"],
                level=stats["level"],
            ))

        # Calculate summary
        total_lane = sum(m.lane_creeps_killed for m in minute_data)
        total_neutral = sum(m.neutral_creeps_killed for m in minute_data)
        total_creeps = total_lane + total_neutral

        # Get gold at start and end for GPM calculation
        start_gold = minute_data[0].gold if minute_data else 0
        end_gold = minute_data[-1].gold if minute_data else 0
        duration_minutes = end_minute - start_minute
        gpm = round((end_gold - start_gold) / duration_minutes, 1) if duration_minutes > 0 else 0

        # CS per minute
        end_cs = minute_data[-1].last_hits if minute_data else 0
        start_cs = minute_data[0].last_hits if minute_data else 0
        cs_per_min = round((end_cs - start_cs) / duration_minutes, 1) if duration_minutes > 0 else 0

        summary = FarmingSummary(
            total_lane_creeps=total_lane,
            total_neutral_creeps=total_neutral,
            jungle_percentage=round(total_neutral / total_creeps * 100, 1) if total_creeps > 0 else 0.0,
            gpm=gpm,
            cs_per_min=cs_per_min,
            camps_cleared=dict(all_camps),
        )

        # Detect transitions
        transitions = self._detect_transitions(creep_kills, minute_data)

        return FarmingPatternResponse(
            success=True,
            match_id=data.match_id,
            hero=hero,
            start_minute=start_minute,
            end_minute=end_minute,
            minutes=minute_data,
            transitions=transitions,
            summary=summary,
            creep_kills=creep_kills,
        )
