"""
Combat log parser for extracting events from Dota 2 replays.

Provides methods to extract hero deaths, combat log events, and detect
fight boundaries using participant connectivity analysis.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from python_manta import MantaParser

from src.models.combat_log import (
    BarracksKill,
    CombatLogEvent,
    CourierKill,
    FightResult,
    HeroDeath,
    ItemPurchase,
    MapLocation,
    RoshanKill,
    TormentorKill,
    TowerKill,
)
from src.utils.position_tracker import position_tracker

logger = logging.getLogger(__name__)


class CombatLogParser:
    """Parses replay files to extract combat log data."""

    COMBATLOG_TYPES = {
        0: "DAMAGE",
        1: "HEAL",
        2: "MODIFIER_ADD",
        3: "MODIFIER_REMOVE",
        4: "DEATH",
        5: "ABILITY",
        6: "ITEM",
        7: "LOCATION",
        8: "GOLD",
        9: "GAME_STATE",
        10: "XP",
        11: "PURCHASE",
        12: "BUYBACK",
        18: "FIRST_BLOOD",
    }

    def __init__(self):
        self._parser = MantaParser()
        self._tick_time_map: Optional[List[Tuple[int, float]]] = None

    def _build_tick_time_map(self, replay_path: Path) -> List[Tuple[int, float]]:
        """
        Build a mapping from tick to game_time using entity snapshots.

        Args:
            replay_path: Path to the replay file

        Returns:
            List of (tick, game_time) tuples for interpolation
        """
        result = self._parser.parse_entities(
            str(replay_path),
            interval_ticks=900,
            max_snapshots=200
        )

        tick_map = []
        for snap in result.snapshots:
            if snap.game_time >= 0:
                tick_map.append((snap.tick, snap.game_time))

        return tick_map

    def _tick_to_game_time(self, tick: int) -> float:
        """
        Convert a tick to game time using interpolation.

        Args:
            tick: The tick value from combat log

        Returns:
            Game time in seconds
        """
        if not self._tick_time_map:
            return 0.0

        before = None
        after = None

        for t, gt in self._tick_time_map:
            if t <= tick:
                before = (t, gt)
            elif after is None:
                after = (t, gt)
                break

        if before is None:
            return 0.0

        if after is None:
            return before[1]

        tick_range = after[0] - before[0]
        time_range = after[1] - before[1]
        tick_offset = tick - before[0]

        return before[1] + (tick_offset / tick_range) * time_range

    def _format_game_time(self, seconds: float) -> str:
        """Format seconds as M:SS string."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def _clean_name(self, name: str) -> str:
        """Remove npc_dota_hero_ prefix from names."""
        if name.startswith("npc_dota_hero_"):
            return name[14:]
        return name

    def _is_hero(self, name: str) -> bool:
        """Check if a name is a hero."""
        return "npc_dota_hero_" in name

    def get_hero_deaths(self, replay_path: Path, include_position: bool = True) -> List[HeroDeath]:
        """
        Get all hero deaths from a replay.

        Args:
            replay_path: Path to the .dem replay file
            include_position: Whether to include map position data (slower)

        Returns:
            List of HeroDeath models with game_time, killer, victim, ability, and position
        """
        if self._tick_time_map is None:
            self._tick_time_map = self._build_tick_time_map(replay_path)

        result = self._parser.parse_combat_log(
            str(replay_path),
            types=[4],  # DEATH events only
            max_entries=10000
        )

        deaths = []
        for entry in result.entries:
            if not self._is_hero(entry.target_name):
                continue

            game_time = self._tick_to_game_time(entry.tick)
            victim_name = self._clean_name(entry.target_name)

            position = None
            if include_position:
                pos = position_tracker.get_hero_position_at_tick(
                    replay_path, victim_name, entry.tick
                )
                if pos:
                    position = MapLocation(
                        x=pos.x,
                        y=pos.y,
                        region=pos.region,
                        lane=pos.lane,
                        location=pos.location
                    )

            deaths.append(HeroDeath(
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                killer=self._clean_name(entry.attacker_name),
                victim=victim_name,
                killer_is_hero=self._is_hero(entry.attacker_name),
                ability=entry.inflictor_name if entry.inflictor_name != "dota_unknown" else None,
                position=position,
            ))

        return deaths

    def get_combat_log(
        self,
        replay_path: Path,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        types: Optional[List[int]] = None,
        hero_filter: Optional[str] = None,
    ) -> List[CombatLogEvent]:
        """
        Get combat log events from a replay with optional filters.

        Args:
            replay_path: Path to the .dem replay file
            start_time: Filter events after this game time (seconds)
            end_time: Filter events before this game time (seconds)
            types: List of event type IDs to include (default: DAMAGE, MODIFIER_ADD, ABILITY, DEATH)
            hero_filter: Only include events involving this hero (cleaned name, e.g. "earthshaker")

        Returns:
            List of CombatLogEvent models
        """
        if self._tick_time_map is None:
            self._tick_time_map = self._build_tick_time_map(replay_path)

        if types is None:
            types = [0, 2, 5, 4]  # DAMAGE, MODIFIER_ADD, ABILITY, DEATH

        result = self._parser.parse_combat_log(
            str(replay_path),
            types=types,
            max_entries=50000
        )

        events = []
        for entry in result.entries:
            game_time = self._tick_to_game_time(entry.tick)

            if start_time is not None and game_time < start_time:
                continue
            if end_time is not None and game_time > end_time:
                continue

            attacker_clean = self._clean_name(entry.attacker_name)
            target_clean = self._clean_name(entry.target_name)

            if hero_filter is not None:
                hero_filter_lower = hero_filter.lower()
                if hero_filter_lower not in attacker_clean.lower() and hero_filter_lower not in target_clean.lower():
                    continue

            event_type = self.COMBATLOG_TYPES.get(entry.type, f"UNKNOWN_{entry.type}")

            events.append(CombatLogEvent(
                type=event_type,
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                attacker=attacker_clean,
                attacker_is_hero=self._is_hero(entry.attacker_name),
                target=target_clean,
                target_is_hero=self._is_hero(entry.target_name),
                ability=entry.inflictor_name if entry.inflictor_name != "dota_unknown" else None,
                value=entry.value if hasattr(entry, 'value') and entry.value else None,
            ))

        return events


    def _find_connected_fight(
        self,
        events: List[CombatLogEvent],
        reference_time: float,
        anchor_hero: Optional[str],
        gap_threshold: float,
    ) -> List[CombatLogEvent]:
        """
        Find events belonging to the same fight using participant connectivity.

        Two events are in the same fight if:
        1. They share a participant (attacker or target)
        2. They are within gap_threshold seconds of each other

        Args:
            events: List of CombatLogEvent models sorted by time
            reference_time: The anchor time (e.g., death time)
            anchor_hero: Optional hero to start the connectivity search from
            gap_threshold: Max seconds between events to consider them connected

        Returns:
            List of CombatLogEvent models belonging to the connected fight
        """
        if not events:
            return []

        hero_combat = [
            e for e in events
            if e.type in ("DAMAGE", "ABILITY", "MODIFIER_ADD", "DEATH")
            and e.attacker_is_hero and e.target_is_hero
            and e.attacker != e.target
        ]

        if not hero_combat:
            return []

        closest_event = None
        closest_diff = float('inf')
        for e in hero_combat:
            diff = abs(e.game_time - reference_time)
            if diff < closest_diff:
                if anchor_hero:
                    anchor_lower = anchor_hero.lower()
                    if anchor_lower in e.attacker.lower() or anchor_lower in e.target.lower():
                        closest_diff = diff
                        closest_event = e
                else:
                    closest_diff = diff
                    closest_event = e

        if not closest_event:
            return []

        fight_participants = {closest_event.attacker.lower(), closest_event.target.lower()}
        fight_events = [closest_event]
        added = True

        while added:
            added = False
            for e in hero_combat:
                if e in fight_events:
                    continue

                attacker_lower = e.attacker.lower()
                target_lower = e.target.lower()

                if attacker_lower not in fight_participants and target_lower not in fight_participants:
                    continue

                is_connected = False
                for fe in fight_events:
                    time_diff = abs(e.game_time - fe.game_time)
                    if time_diff <= gap_threshold:
                        fe_attacker = fe.attacker.lower()
                        fe_target = fe.target.lower()
                        if (attacker_lower in (fe_attacker, fe_target) or
                            target_lower in (fe_attacker, fe_target)):
                            is_connected = True
                            break

                if is_connected:
                    fight_events.append(e)
                    fight_participants.add(attacker_lower)
                    fight_participants.add(target_lower)
                    added = True

        return sorted(fight_events, key=lambda x: x.game_time)

    def get_combat_timespan(
        self,
        replay_path: Path,
        reference_time: float,
        hero: Optional[str] = None,
        gap_threshold: float = 3.0,
        max_lookback: float = 30.0,
    ) -> FightResult:
        """
        Get combat log for a fight around a reference time (e.g., a death).

        Detects fight boundaries using participant connectivity - events are grouped
        into the same fight if they share participants and are within gap_threshold.
        Separate skirmishes (e.g., mid fight vs safelane fight) are correctly separated.

        Args:
            replay_path: Path to the .dem replay file
            reference_time: Reference game time in seconds (e.g., death time)
            hero: Optional hero name to anchor the fight detection
            gap_threshold: Seconds between events to consider them connected
            max_lookback: Maximum seconds to look back from reference_time

        Returns:
            FightResult model with fight boundaries, participants, and events
        """
        if self._tick_time_map is None:
            self._tick_time_map = self._build_tick_time_map(replay_path)

        search_start = max(0, reference_time - max_lookback)
        search_end = reference_time + 2

        all_events = self.get_combat_log(
            replay_path,
            start_time=search_start,
            end_time=search_end,
            hero_filter=None,
        )

        if not all_events:
            return FightResult(
                fight_start=reference_time,
                fight_start_str=self._format_game_time(reference_time),
                fight_end=reference_time,
                fight_end_str=self._format_game_time(reference_time),
                duration=0,
                participants=[],
                total_events=0,
                events=[],
            )

        connected_events = self._find_connected_fight(
            all_events, reference_time, hero, gap_threshold
        )

        if not connected_events:
            return FightResult(
                fight_start=reference_time,
                fight_start_str=self._format_game_time(reference_time),
                fight_end=reference_time,
                fight_end_str=self._format_game_time(reference_time),
                duration=0,
                participants=[],
                total_events=0,
                events=[],
            )

        fight_start = connected_events[0].game_time
        fight_end = connected_events[-1].game_time

        participants = set()
        for e in connected_events:
            if e.attacker_is_hero:
                participants.add(e.attacker)
            if e.target_is_hero:
                participants.add(e.target)

        participants_lower = [p.lower() for p in participants]
        fight_events = [
            e for e in all_events
            if e.game_time >= fight_start and e.game_time <= fight_end
            and (e.attacker.lower() in participants_lower
                 or e.target.lower() in participants_lower)
        ]

        return FightResult(
            fight_start=round(fight_start, 1),
            fight_start_str=self._format_game_time(fight_start),
            fight_end=round(fight_end, 1),
            fight_end_str=self._format_game_time(fight_end),
            duration=round(fight_end - fight_start, 1),
            participants=sorted(participants),
            total_events=len(fight_events),
            events=fight_events,
        )

    def get_item_purchases(
        self,
        replay_path: Path,
        hero_filter: Optional[str] = None,
    ) -> List[ItemPurchase]:
        """
        Get item purchase events from a replay.

        Args:
            replay_path: Path to the .dem replay file
            hero_filter: Only include purchases by this hero (e.g., "juggernaut")

        Returns:
            List of ItemPurchase models sorted by game time
        """
        result = self._parser.parse_combat_log(
            str(replay_path),
            types=[11],  # PURCHASE events
            max_entries=5000
        )

        purchases = []
        for entry in result.entries:
            if not entry.target_name or "hero" not in entry.target_name.lower():
                continue

            hero = self._clean_name(entry.target_name)

            if hero_filter:
                if hero_filter.lower() not in hero.lower():
                    continue

            game_time = entry.game_time

            purchases.append(ItemPurchase(
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                hero=hero,
                item=entry.value_name,
            ))

        return sorted(purchases, key=lambda x: x.game_time)

    def get_courier_kills(self, replay_path: Path, include_position: bool = True) -> List[CourierKill]:
        """
        Get courier kill events from a replay.

        Args:
            replay_path: Path to the .dem replay file
            include_position: Whether to include map position data

        Returns:
            List of CourierKill models sorted by game time
        """
        result = self._parser.parse_combat_log(
            str(replay_path),
            types=[4],  # DEATH events
            max_entries=5000
        )

        kills = []
        for entry in result.entries:
            if "courier" not in entry.target_name.lower():
                continue

            game_time = entry.game_time
            killer = self._clean_name(entry.attacker_name)
            owner = self._clean_name(entry.target_source_name)

            # Determine team from target_team field
            # Team 2 = Radiant, Team 3 = Dire
            if entry.target_team == 2:
                team = "radiant"
            elif entry.target_team == 3:
                team = "dire"
            else:
                team = "unknown"

            # Get position from killer's location (courier position not easily queryable)
            position = None
            if include_position and self._is_hero(entry.attacker_name):
                pos = position_tracker.get_hero_position_at_tick(
                    replay_path, killer, entry.tick
                )
                if pos:
                    position = MapLocation(
                        x=pos.x,
                        y=pos.y,
                        region=pos.region,
                        lane=pos.lane,
                        location=pos.location
                    )

            kills.append(CourierKill(
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                killer=killer,
                killer_is_hero=self._is_hero(entry.attacker_name),
                owner=owner,
                team=team,
                position=position,
            ))

        return sorted(kills, key=lambda x: x.game_time)

    def get_objective_kills(
        self,
        replay_path: Path,
    ) -> Tuple[List[RoshanKill], List[TormentorKill], List[TowerKill], List[BarracksKill]]:
        """
        Get objective kill events from a replay (Roshan, Tormentor, towers, barracks).

        Args:
            replay_path: Path to the .dem replay file

        Returns:
            Tuple of (roshan_kills, tormentor_kills, tower_kills, barracks_kills)
        """
        result = self._parser.parse_combat_log(
            str(replay_path),
            types=[4],  # DEATH events
            max_entries=10000
        )

        roshan_kills = []
        tormentor_kills = []
        tower_kills = []
        barracks_kills = []
        roshan_count = 0

        for entry in result.entries:
            target = entry.target_name.lower()
            game_time = entry.game_time
            killer = self._clean_name(entry.attacker_name)

            # Roshan kills
            if "roshan" in target:
                roshan_count += 1
                # Roshan killer team: if killer is a hero, determine team
                # Team 2 = Radiant, Team 3 = Dire
                if entry.attacker_team == 2:
                    team = "radiant"
                elif entry.attacker_team == 3:
                    team = "dire"
                else:
                    team = "unknown"

                roshan_kills.append(RoshanKill(
                    game_time=round(game_time, 1),
                    game_time_str=self._format_game_time(game_time),
                    killer=killer,
                    team=team,
                    kill_number=roshan_count,
                ))

            # Tormentor kills (miniboss)
            elif "miniboss" in target:
                # Determine which side's Tormentor based on killer team
                if entry.attacker_team == 2:
                    team = "radiant"
                    side = "radiant"  # Radiant usually kills their own side Tormentor
                elif entry.attacker_team == 3:
                    team = "dire"
                    side = "dire"
                else:
                    team = "unknown"
                    side = "unknown"

                tormentor_kills.append(TormentorKill(
                    game_time=round(game_time, 1),
                    game_time_str=self._format_game_time(game_time),
                    killer=killer,
                    team=team,
                    side=side,
                ))

            # Tower kills
            elif "tower" in target and ("goodguys" in target or "badguys" in target):
                # Parse tower info from name like "npc_dota_goodguys_tower1_mid"
                team = "radiant" if "goodguys" in target else "dire"

                # Extract tier
                tier = 1
                if "tower1" in target:
                    tier = 1
                elif "tower2" in target:
                    tier = 2
                elif "tower3" in target:
                    tier = 3
                elif "tower4" in target:
                    tier = 4

                # Extract lane
                lane = "unknown"
                if "_top" in target:
                    lane = "top"
                elif "_mid" in target:
                    lane = "mid"
                elif "_bot" in target:
                    lane = "bot"
                elif tier == 4:
                    lane = "base"

                # Build a cleaner tower name
                tower_name = f"{team}_t{tier}_{lane}"

                tower_kills.append(TowerKill(
                    game_time=round(game_time, 1),
                    game_time_str=self._format_game_time(game_time),
                    tower=tower_name,
                    team=team,
                    tier=tier,
                    lane=lane,
                    killer=killer,
                    killer_is_hero=self._is_hero(entry.attacker_name),
                ))

            # Barracks kills
            elif "rax" in target and ("goodguys" in target or "badguys" in target):
                # Parse barracks info from name like "npc_dota_goodguys_melee_rax_mid"
                team = "radiant" if "goodguys" in target else "dire"

                # Extract type
                rax_type = "melee" if "melee" in target else "ranged"

                # Extract lane
                lane = "unknown"
                if "_top" in target:
                    lane = "top"
                elif "_mid" in target:
                    lane = "mid"
                elif "_bot" in target:
                    lane = "bot"

                # Build cleaner barracks name
                barracks_name = f"{team}_{rax_type}_{lane}"

                barracks_kills.append(BarracksKill(
                    game_time=round(game_time, 1),
                    game_time_str=self._format_game_time(game_time),
                    barracks=barracks_name,
                    team=team,
                    lane=lane,
                    type=rax_type,
                    killer=killer,
                    killer_is_hero=self._is_hero(entry.attacker_name),
                ))

        return (
            sorted(roshan_kills, key=lambda x: x.game_time),
            sorted(tormentor_kills, key=lambda x: x.game_time),
            sorted(tower_kills, key=lambda x: x.game_time),
            sorted(barracks_kills, key=lambda x: x.game_time),
        )


combat_log_parser = CombatLogParser()
