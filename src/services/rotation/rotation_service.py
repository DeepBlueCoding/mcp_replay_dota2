"""
Rotation service for analyzing hero movement patterns between lanes.

Detects rotations, correlates with runes and fights, links to outcomes.
NO MCP DEPENDENCIES.
"""

import logging
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ..combat.combat_service import CombatService
from ..combat.fight_service import FightService
from ..models.combat_data import Fight, HeroDeath, RunePickup
from ..models.replay_data import ParsedReplayData
from ..models.rotation_data import (
    HeroRotationStats,
    PowerRuneEvent,
    Rotation,
    RotationAnalysisResponse,
    RotationOutcome,
    RotationSummary,
    RuneCorrelation,
    RuneRotations,
    WisdomRuneEvent,
)

logger = logging.getLogger(__name__)

# Lane boundaries (approximate, based on position_tracker.py)
LANE_BOUNDARIES = {
    "top": {"x_min": -8000, "x_max": 0, "y_min": 2000, "y_max": 8000},
    "mid": {"x_min": -3500, "x_max": 3500, "y_min": -3500, "y_max": 3500},
    "bot": {"x_min": 0, "x_max": 8000, "y_min": -8000, "y_max": -2000},
}

# Rune positions
POWER_RUNE_TOP = (-1900, 1200)
POWER_RUNE_BOT = (2400, -1800)
WISDOM_RUNE_RADIANT = (-6200, 1000)
WISDOM_RUNE_DIRE = (5800, -1400)

# Timings
POWER_RUNE_FIRST_SPAWN = 360  # 6:00
POWER_RUNE_INTERVAL = 120  # every 2 min
WISDOM_RUNE_FIRST_SPAWN = 420  # 7:00
WISDOM_RUNE_INTERVAL = 420  # every 7 min

# Detection thresholds
ROTATION_CORRELATION_WINDOW = 60.0  # seconds to look for rune/kill correlation
WISDOM_FIGHT_RADIUS = 2000  # units from wisdom rune to count as "nearby"
MIN_ROTATION_DURATION = 15.0  # minimum seconds away from lane to count as rotation


class RotationService:
    """
    Service for rotation pattern analysis.

    Provides:
    - Lane assignment detection
    - Rotation detection (hero leaves lane)
    - Rune correlation
    - Fight outcome linking
    - Wisdom rune fight detection
    """

    def __init__(
        self,
        combat_service: Optional[CombatService] = None,
        fight_service: Optional[FightService] = None,
    ):
        self._combat = combat_service or CombatService()
        self._fight = fight_service or FightService()

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

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def _classify_lane(self, x: float, y: float) -> str:
        """Classify position to a lane."""
        # Check mid first (smallest area)
        if (LANE_BOUNDARIES["mid"]["x_min"] <= x <= LANE_BOUNDARIES["mid"]["x_max"] and
                LANE_BOUNDARIES["mid"]["y_min"] <= y <= LANE_BOUNDARIES["mid"]["y_max"]):
            return "mid"

        # Check top
        if (LANE_BOUNDARIES["top"]["x_min"] <= x <= LANE_BOUNDARIES["top"]["x_max"] and
                LANE_BOUNDARIES["top"]["y_min"] <= y <= LANE_BOUNDARIES["top"]["y_max"]):
            return "top"

        # Check bot
        if (LANE_BOUNDARIES["bot"]["x_min"] <= x <= LANE_BOUNDARIES["bot"]["x_max"] and
                LANE_BOUNDARIES["bot"]["y_min"] <= y <= LANE_BOUNDARIES["bot"]["y_max"]):
            return "bot"

        return "jungle"

    def _get_lane_assignments(
        self,
        data: ParsedReplayData,
    ) -> Dict[str, Tuple[str, str]]:
        """
        Determine lane assignments from minute 2-3 positions.

        Returns:
            Dict mapping hero name to (lane, role)
        """
        assignments: Dict[str, Tuple[str, str]] = {}

        # Look at snapshots between minute 2-3
        target_start = 120  # 2:00
        target_end = 180  # 3:00

        lane_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for snapshot in data.entity_snapshots:
            if snapshot.game_time < target_start or snapshot.game_time > target_end:
                continue

            for hero_snap in snapshot.heroes:
                hero = self._clean_hero_name(hero_snap.hero_name)
                if not hero:
                    continue

                lane = self._classify_lane(hero_snap.x, hero_snap.y)
                lane_counts[hero][lane] += 1

        # Assign each hero to their most common lane
        for hero, counts in lane_counts.items():
            if not counts:
                continue
            primary_lane = max(counts, key=counts.get)

            # Infer role from lane and team
            # This is simplified - real role detection would be more complex
            if primary_lane == "mid":
                role = "mid"
            elif primary_lane == "jungle":
                role = "support"  # Roaming support
            else:
                # Would need team info to distinguish carry vs offlane
                role = "core"

            assignments[hero] = (primary_lane, role)

        return assignments

    def _get_hero_position_at_time(
        self,
        data: ParsedReplayData,
        hero: str,
        target_time: float,
    ) -> Optional[Tuple[float, float, str]]:
        """
        Get hero position at a specific time.

        Returns:
            Tuple of (x, y, lane) or None if not found
        """
        hero_lower = hero.lower()
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot or min_diff > 30:  # Too far from target time
            return None

        for hero_snap in best_snapshot.heroes:
            player_hero = self._clean_hero_name(hero_snap.hero_name)
            if hero_lower in player_hero.lower():
                lane = self._classify_lane(hero_snap.x, hero_snap.y)
                return (hero_snap.x, hero_snap.y, lane)

        return None

    def _find_rune_before_rotation(
        self,
        rune_pickups: List[RunePickup],
        hero: str,
        rotation_time: float,
    ) -> Optional[RuneCorrelation]:
        """Find rune pickup by hero within 60s before rotation."""
        hero_lower = hero.lower()

        for pickup in rune_pickups:
            if hero_lower not in pickup.hero.lower():
                continue

            time_diff = rotation_time - pickup.game_time
            if 0 < time_diff <= ROTATION_CORRELATION_WINDOW:
                return RuneCorrelation(
                    rune_type=pickup.rune_type,
                    pickup_time=pickup.game_time,
                    pickup_time_str=pickup.game_time_str,
                    seconds_before_rotation=round(time_diff, 1),
                )

        return None

    def _find_fight_outcome(
        self,
        fights: List[Fight],
        deaths: List[HeroDeath],
        hero: str,
        rotation_time: float,
        to_lane: str,
    ) -> RotationOutcome:
        """Determine outcome of rotation from fights and deaths."""
        hero_lower = hero.lower()

        # Look for deaths within window after rotation
        deaths_in_window = []
        for death in deaths:
            if rotation_time <= death.game_time <= rotation_time + ROTATION_CORRELATION_WINDOW:
                deaths_in_window.append(death)

        if not deaths_in_window:
            return RotationOutcome(type="no_engagement", deaths_in_window=0)

        # Check if rotating hero died
        hero_died = any(
            hero_lower in d.victim.lower() for d in deaths_in_window
        )

        # Check kills by rotating hero
        kills_by_hero = [
            d.victim for d in deaths_in_window
            if hero_lower in d.killer.lower()
        ]

        # Find associated fight
        fight_id = None
        for fight in fights:
            if (fight.start_time <= rotation_time + ROTATION_CORRELATION_WINDOW and
                    fight.end_time >= rotation_time):
                if any(hero_lower in p.lower() for p in fight.participants):
                    fight_id = fight.fight_id
                    break

        # Determine outcome type
        if hero_died and kills_by_hero:
            outcome_type = "traded"
        elif hero_died:
            outcome_type = "died"
        elif kills_by_hero:
            outcome_type = "kill"
        elif fight_id:
            outcome_type = "fight"
        else:
            outcome_type = "no_engagement"

        return RotationOutcome(
            type=outcome_type,
            fight_id=fight_id,
            deaths_in_window=len(deaths_in_window),
            rotation_hero_died=hero_died,
            kills_by_rotation_hero=kills_by_hero,
        )

    def _detect_rotations(
        self,
        data: ParsedReplayData,
        lane_assignments: Dict[str, Tuple[str, str]],
        rune_pickups: List[RunePickup],
        deaths: List[HeroDeath],
        fights: List[Fight],
        start_minute: int,
        end_minute: int,
    ) -> List[Rotation]:
        """
        Detect all rotations in the time range.

        Algorithm:
        - Sample positions every 30 seconds
        - Track when hero is not in assigned lane
        - Create rotation when hero is away for MIN_ROTATION_DURATION
        """
        rotations = []
        rotation_counter = 0

        # Track rotation state per hero
        rotation_state: Dict[str, Dict] = {}

        start_time = start_minute * 60.0
        end_time = end_minute * 60.0
        sample_interval = 30.0  # Check every 30 seconds

        current_time = start_time
        while current_time <= end_time:
            for hero, (assigned_lane, role) in lane_assignments.items():
                pos = self._get_hero_position_at_time(data, hero, current_time)
                if not pos:
                    continue

                x, y, current_lane = pos

                # Check if hero is away from assigned lane
                is_away = current_lane != assigned_lane and current_lane != "jungle"

                if hero not in rotation_state:
                    rotation_state[hero] = {
                        "away": False,
                        "away_start": None,
                        "to_lane": None,
                    }

                state = rotation_state[hero]

                if is_away and not state["away"]:
                    # Started rotation
                    state["away"] = True
                    state["away_start"] = current_time
                    state["to_lane"] = current_lane

                elif not is_away and state["away"]:
                    # Ended rotation
                    duration = current_time - state["away_start"]
                    if duration >= MIN_ROTATION_DURATION:
                        rotation_counter += 1
                        rotation_id = f"rot_{rotation_counter}"

                        # Find rune correlation
                        rune_before = self._find_rune_before_rotation(
                            rune_pickups, hero, state["away_start"]
                        )

                        # Find fight outcome
                        outcome = self._find_fight_outcome(
                            fights, deaths, hero, state["away_start"], state["to_lane"]
                        )

                        rotations.append(Rotation(
                            rotation_id=rotation_id,
                            hero=hero,
                            role=role,
                            game_time=state["away_start"],
                            game_time_str=self._format_time(state["away_start"]),
                            from_lane=assigned_lane,
                            to_lane=state["to_lane"],
                            rune_before=rune_before,
                            outcome=outcome,
                            travel_time_seconds=round(duration, 1),
                            returned_to_lane=True,
                            return_time=current_time,
                            return_time_str=self._format_time(current_time),
                        ))

                    # Reset state
                    state["away"] = False
                    state["away_start"] = None
                    state["to_lane"] = None

            current_time += sample_interval

        return sorted(rotations, key=lambda r: r.game_time)

    def _build_power_rune_events(
        self,
        rune_pickups: List[RunePickup],
        rotations: List[Rotation],
        start_minute: int,
        end_minute: int,
    ) -> List[PowerRuneEvent]:
        """Build power rune event list with rotation correlation."""
        events = []

        start_time = start_minute * 60.0
        end_time = end_minute * 60.0

        # Generate expected spawn times
        spawn_time = POWER_RUNE_FIRST_SPAWN
        while spawn_time <= end_time:
            if spawn_time >= start_time:
                # Check for pickups around this spawn
                for location in ["top", "bot"]:
                    # Find pickup near this time
                    pickup = None
                    for p in rune_pickups:
                        if abs(p.game_time - spawn_time) <= 30:  # Within 30s of spawn
                            pickup = p
                            break

                    # Check if led to rotation
                    led_to_rotation = False
                    rotation_id = None
                    if pickup:
                        for rot in rotations:
                            if (rot.rune_before and
                                    rot.rune_before.pickup_time == pickup.game_time):
                                led_to_rotation = True
                                rotation_id = rot.rotation_id
                                break

                    events.append(PowerRuneEvent(
                        spawn_time=spawn_time,
                        spawn_time_str=self._format_time(spawn_time),
                        location=location,
                        taken_by=pickup.hero if pickup else None,
                        pickup_time=pickup.game_time if pickup else None,
                        led_to_rotation=led_to_rotation,
                        rotation_id=rotation_id,
                    ))

            spawn_time += POWER_RUNE_INTERVAL

        return events

    def _build_wisdom_rune_events(
        self,
        deaths: List[HeroDeath],
        fights: List[Fight],
        start_minute: int,
        end_minute: int,
    ) -> List[WisdomRuneEvent]:
        """Build wisdom rune event list with fight correlation."""
        events = []

        start_time = start_minute * 60.0
        end_time = end_minute * 60.0

        spawn_time = WISDOM_RUNE_FIRST_SPAWN
        while spawn_time <= end_time:
            if spawn_time >= start_time:
                for location, pos in [
                    ("radiant_jungle", WISDOM_RUNE_RADIANT),
                    ("dire_jungle", WISDOM_RUNE_DIRE)
                ]:
                    # Count deaths near this position around spawn time
                    nearby_deaths = []
                    for death in deaths:
                        if abs(death.game_time - spawn_time) > 60:
                            continue
                        if death.position_x is None or death.position_y is None:
                            continue
                        dist = self._distance(
                            (death.position_x, death.position_y), pos
                        )
                        if dist <= WISDOM_FIGHT_RADIUS:
                            nearby_deaths.append(death)

                    # Find associated fight
                    fight_id = None
                    for fight in fights:
                        if abs(fight.start_time - spawn_time) <= 60:
                            # Check if any death was near wisdom rune
                            for d in fight.deaths:
                                if d in nearby_deaths:
                                    fight_id = fight.fight_id
                                    break
                            if fight_id:
                                break

                    events.append(WisdomRuneEvent(
                        spawn_time=spawn_time,
                        spawn_time_str=self._format_time(spawn_time),
                        location=location,
                        taken_by=None,  # Can't detect wisdom pickup from combat log
                        contested=len(nearby_deaths) > 0,
                        fight_id=fight_id,
                        deaths_nearby=len(nearby_deaths),
                    ))

            spawn_time += WISDOM_RUNE_INTERVAL

        return events

    def _build_summary(
        self,
        rotations: List[Rotation],
        lane_assignments: Dict[str, Tuple[str, str]],
        wisdom_events: List[WisdomRuneEvent],
    ) -> RotationSummary:
        """Build summary statistics."""
        by_hero: Dict[str, HeroRotationStats] = {}

        for hero, (lane, role) in lane_assignments.items():
            hero_rotations = [r for r in rotations if r.hero == hero]

            successful = sum(1 for r in hero_rotations if r.outcome.type == "kill")
            failed = sum(1 for r in hero_rotations
                         if r.outcome.type in ("died", "no_engagement"))
            trades = sum(1 for r in hero_rotations if r.outcome.type == "traded")
            rune_rots = sum(1 for r in hero_rotations if r.rune_before is not None)

            by_hero[hero] = HeroRotationStats(
                hero=hero,
                role=role,
                total_rotations=len(hero_rotations),
                successful_ganks=successful,
                failed_ganks=failed,
                trades=trades,
                rune_rotations=rune_rots,
            )

        # Count runes leading to kills
        runes_to_kills = sum(
            1 for r in rotations
            if r.rune_before and r.outcome.type in ("kill", "traded")
        )

        # Count wisdom fights
        wisdom_fights = sum(1 for w in wisdom_events if w.contested)

        # Most active rotator
        most_active = None
        max_rotations = 0
        for hero, stats in by_hero.items():
            if stats.total_rotations > max_rotations:
                max_rotations = stats.total_rotations
                most_active = hero

        return RotationSummary(
            total_rotations=len(rotations),
            by_hero=by_hero,
            runes_leading_to_kills=runes_to_kills,
            wisdom_rune_fights=wisdom_fights,
            most_active_rotator=most_active,
        )

    def get_rotation_analysis(
        self,
        data: ParsedReplayData,
        start_minute: int = 0,
        end_minute: int = 20,
    ) -> RotationAnalysisResponse:
        """
        Analyze rotations in a match.

        Args:
            data: ParsedReplayData from ReplayService
            start_minute: Start of analysis range (default: 0)
            end_minute: End of analysis range (default: 20)

        Returns:
            RotationAnalysisResponse with all rotation data
        """
        # Get lane assignments from early game
        lane_assignments = self._get_lane_assignments(data)

        if not lane_assignments:
            return RotationAnalysisResponse(
                success=False,
                match_id=data.match_id,
                start_minute=start_minute,
                end_minute=end_minute,
                error="Could not determine lane assignments",
            )

        # Get supporting data
        rune_pickups = self._combat.get_rune_pickups(data)
        deaths = self._combat.get_hero_deaths(data)
        fight_result = self._fight.get_all_fights(data)
        fights = fight_result.fights

        # Detect rotations
        rotations = self._detect_rotations(
            data, lane_assignments, rune_pickups, deaths, fights,
            start_minute, end_minute,
        )

        # Build rune events
        power_runes = self._build_power_rune_events(
            rune_pickups, rotations, start_minute, end_minute
        )
        wisdom_runes = self._build_wisdom_rune_events(
            deaths, fights, start_minute, end_minute
        )

        # Build summary
        summary = self._build_summary(rotations, lane_assignments, wisdom_runes)

        return RotationAnalysisResponse(
            success=True,
            match_id=data.match_id,
            start_minute=start_minute,
            end_minute=end_minute,
            rotations=rotations,
            rune_events=RuneRotations(
                power_runes=power_runes,
                wisdom_runes=wisdom_runes,
            ),
            summary=summary,
        )
