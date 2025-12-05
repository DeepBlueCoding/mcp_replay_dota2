"""
Combat log parser for extracting events from Dota 2 replays.

Provides methods to extract hero deaths, combat log events, and detect
fight boundaries using participant connectivity analysis.

Uses replay_cache to avoid repeated parsing of large replay files.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from python_manta import CombatLogType, Team

from src.models.combat_log import (
    BarracksKill,
    CombatLogEvent,
    CourierKill,
    FightResult,
    HeroDeath,
    ItemPurchase,
    MapLocation,
    RoshanKill,
    RunePickup,
    TormentorKill,
    TowerKill,
)
from src.utils.constants_fetcher import constants_fetcher
from src.utils.position_tracker import classify_map_position
from src.utils.replay_cache import ParsedReplayData, replay_cache

logger = logging.getLogger(__name__)


class CombatLogParser:
    """Parses replay files to extract combat log data using cached replay data."""

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
        13: "ABILITY_TRIGGER",
        18: "FIRST_BLOOD",
    }

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

    def _get_position_at_tick(
        self, data: ParsedReplayData, hero_name: str, tick: int
    ) -> Optional[MapLocation]:
        """Get hero position at tick using cached data."""
        pos = replay_cache.get_hero_position_at_tick(data, hero_name, tick)
        if pos:
            map_pos = classify_map_position(pos[0], pos[1])
            return MapLocation(
                x=map_pos.x,
                y=map_pos.y,
                region=map_pos.region,
                lane=map_pos.lane,
                location=map_pos.location,
            )
        return None

    def get_hero_deaths(self, replay_path: Path, include_position: bool = True) -> List[HeroDeath]:
        """
        Get all hero deaths from a replay.

        Args:
            replay_path: Path to the .dem replay file
            include_position: Whether to include map position data

        Returns:
            List of HeroDeath models with game_time, killer, victim, ability, and position
        """
        data = replay_cache.get_parsed_data(replay_path)

        deaths = []
        for entry in data.combat_log:
            if entry.type != 4:  # DEATH
                continue
            if not self._is_hero(entry.target_name):
                continue

            game_time = replay_cache.tick_to_game_time(data, entry.tick)
            victim_name = self._clean_name(entry.target_name)

            position = None
            if include_position:
                position = self._get_position_at_tick(data, victim_name, entry.tick)

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

    def _is_self_buff_ability(self, ability_name: str) -> bool:
        """
        Check if an ability is a self-buff (No Target behavior).

        Self-buff abilities cannot "miss" - they always apply to the caster.
        Examples: Enchant Totem, Rage, Blade Fury, Mirror Image
        """
        abilities = constants_fetcher.get_abilities_constants()
        if not abilities:
            return False

        ability_data = abilities.get(ability_name, {})
        behavior = ability_data.get("behavior", "")

        # behavior can be a string or list
        if isinstance(behavior, list):
            return "No Target" in behavior
        return behavior == "No Target"

    def _normalize_ability_name(self, name: str) -> str:
        """
        Normalize ability/modifier name for comparison.

        MODIFIER_ADD events often have 'modifier_' prefix that ABILITY events don't have.
        E.g., ABILITY has 'naga_siren_ensnare', MODIFIER_ADD has 'modifier_naga_siren_ensnare'
        """
        if name.startswith("modifier_"):
            return name[9:]  # len("modifier_") = 9
        return name

    def _build_ability_hit_index(self, data: ParsedReplayData, time_window: float = 2.0) -> dict:
        """
        Build an index of which ability casts resulted in damage/effects on enemy heroes.

        For each (caster, ability, cast_time), tracks whether there was a subsequent
        DAMAGE or MODIFIER_ADD event on an enemy hero within the time window.

        Self-buff abilities (No Target behavior) are marked as None (not applicable).

        Returns:
            Dict mapping (caster_name, ability_name, cast_tick) -> bool|None
            - True: ability hit an enemy hero
            - False: ability missed (no enemy heroes hit)
            - None: not applicable (self-buff ability)
        """
        ability_casts = []
        damage_effects = []

        for entry in data.combat_log:
            game_time = replay_cache.tick_to_game_time(data, entry.tick)

            if entry.type == CombatLogType.ABILITY.value:
                if self._is_hero(entry.attacker_name) and entry.inflictor_name:
                    ability_casts.append({
                        "caster": entry.attacker_name,
                        "ability": entry.inflictor_name,
                        "time": game_time,
                        "tick": entry.tick,
                    })
            elif entry.type in (CombatLogType.DAMAGE.value, CombatLogType.MODIFIER_ADD.value):
                if self._is_hero(entry.attacker_name) and self._is_hero(entry.target_name):
                    if entry.attacker_name != entry.target_name and entry.inflictor_name:
                        damage_effects.append({
                            "caster": entry.attacker_name,
                            "ability": entry.inflictor_name,
                            "time": game_time,
                        })

        hit_index = {}
        for cast in ability_casts:
            key = (cast["caster"], cast["ability"], cast["tick"])

            # Self-buff abilities can't miss - mark as N/A
            if self._is_self_buff_ability(cast["ability"]):
                hit_index[key] = None
                continue

            # Check if offensive ability hit an enemy hero
            # Normalize ability names to handle modifier_ prefix difference
            cast_ability_normalized = self._normalize_ability_name(cast["ability"])
            hit = any(
                d["caster"] == cast["caster"]
                and self._normalize_ability_name(d["ability"]) == cast_ability_normalized
                and cast["time"] <= d["time"] <= cast["time"] + time_window
                for d in damage_effects
            )
            hit_index[key] = hit

        return hit_index

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
            List of CombatLogEvent models. ABILITY events include 'hit' field indicating
            whether the ability damaged/affected an enemy hero.
        """
        data = replay_cache.get_parsed_data(replay_path)

        if types is None:
            types = [
                CombatLogType.DAMAGE.value,
                CombatLogType.MODIFIER_ADD.value,
                CombatLogType.ABILITY.value,
                CombatLogType.DEATH.value,
                CombatLogType.ABILITY_TRIGGER.value,
            ]

        # Build hit index for ability events
        hit_index = self._build_ability_hit_index(data) if CombatLogType.ABILITY.value in types else {}

        events = []
        for entry in data.combat_log:
            if entry.type not in types:
                continue

            game_time = replay_cache.tick_to_game_time(data, entry.tick)

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

            # Determine hit status for ABILITY events
            hit = None
            if entry.type == CombatLogType.ABILITY.value and self._is_hero(entry.attacker_name) and entry.inflictor_name:
                key = (entry.attacker_name, entry.inflictor_name, entry.tick)
                hit = hit_index.get(key, False)

            events.append(CombatLogEvent(
                type=event_type,
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                attacker=attacker_clean,
                attacker_is_hero=self._is_hero(entry.attacker_name),
                target=target_clean,
                target_is_hero=self._is_hero(entry.target_name),
                ability=entry.inflictor_name if entry.inflictor_name != "dota_unknown" else None,
                value=entry.value if entry.value else None,
                hit=hit,
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

        Includes ability casts (even AoE/self-cast) from fight participants.
        """
        if not events:
            return []

        # Hero-vs-hero combat events for establishing fight participants
        # ABILITY_TRIGGER includes Lotus Orb reflections (attacker=buff holder, target=spell caster)
        hero_combat = [
            e for e in events
            if e.type in ("DAMAGE", "ABILITY", "MODIFIER_ADD", "DEATH", "ABILITY_TRIGGER")
            and e.attacker_is_hero and e.target_is_hero
            and e.attacker != e.target
        ]

        # Ability casts by heroes (including AoE/self-cast where target is unknown)
        ability_casts = [
            e for e in events
            if e.type == "ABILITY"
            and e.attacker_is_hero
            and not e.target_is_hero  # AoE or self-cast
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

        # Now add ability casts from fight participants (including whiffs)
        fight_start = min(e.game_time for e in fight_events)
        fight_end = max(e.game_time for e in fight_events)

        for e in ability_casts:
            if e in fight_events:
                continue
            attacker_lower = e.attacker.lower()
            # Include if caster is a fight participant and within fight time bounds
            if attacker_lower in fight_participants:
                if fight_start - 1 <= e.game_time <= fight_end + 1:
                    fight_events.append(e)

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

        Detects fight boundaries using participant connectivity.
        """
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
        data = replay_cache.get_parsed_data(replay_path)

        purchases = []
        for entry in data.combat_log:
            if entry.type != 11:  # PURCHASE
                continue
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
        data = replay_cache.get_parsed_data(replay_path)

        kills = []
        for entry in data.combat_log:
            if entry.type != 4:  # DEATH
                continue
            if "courier" not in entry.target_name.lower():
                continue

            game_time = entry.game_time
            killer = self._clean_name(entry.attacker_name)
            owner = self._clean_name(entry.target_source_name)

            if entry.target_team == Team.RADIANT.value:
                team = "radiant"
            elif entry.target_team == Team.DIRE.value:
                team = "dire"
            else:
                team = "unknown"

            position = None
            if include_position and self._is_hero(entry.attacker_name):
                position = self._get_position_at_tick(data, killer, entry.tick)

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
        data = replay_cache.get_parsed_data(replay_path)

        roshan_kills = []
        tormentor_kills = []
        tower_kills = []
        barracks_kills = []
        roshan_count = 0

        for entry in data.combat_log:
            if entry.type != 4:  # DEATH
                continue

            target = entry.target_name.lower()
            game_time = entry.game_time
            killer = self._clean_name(entry.attacker_name)

            # Roshan kills
            if "roshan" in target:
                roshan_count += 1
                if entry.attacker_team == Team.RADIANT.value:
                    team = "radiant"
                elif entry.attacker_team == Team.DIRE.value:
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

            # Tormentor kills
            elif "miniboss" in target:
                if entry.attacker_team == Team.RADIANT.value:
                    team = "radiant"
                    side = "radiant"
                elif entry.attacker_team == Team.DIRE.value:
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
                team = "radiant" if "goodguys" in target else "dire"

                tier = 1
                if "tower1" in target:
                    tier = 1
                elif "tower2" in target:
                    tier = 2
                elif "tower3" in target:
                    tier = 3
                elif "tower4" in target:
                    tier = 4

                lane = "unknown"
                if "_top" in target:
                    lane = "top"
                elif "_mid" in target:
                    lane = "mid"
                elif "_bot" in target:
                    lane = "bot"
                elif tier == 4:
                    lane = "base"

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
                team = "radiant" if "goodguys" in target else "dire"
                rax_type = "melee" if "melee" in target else "ranged"

                lane = "unknown"
                if "_top" in target:
                    lane = "top"
                elif "_mid" in target:
                    lane = "mid"
                elif "_bot" in target:
                    lane = "bot"

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

    def get_rune_pickups(self, replay_path: Path) -> List[RunePickup]:
        """
        Get power rune pickup events from a replay.

        Power runes are tracked via MODIFIER_ADD events when a hero gains a rune buff.
        Note: Bounty and wisdom runes are not trackable this way as they don't grant buffs.

        Args:
            replay_path: Path to the .dem replay file

        Returns:
            List of RunePickup models sorted by game time
        """
        from python_manta import RuneType

        data = replay_cache.get_parsed_data(replay_path)

        pickups = []
        for entry in data.combat_log:
            if entry.type != 2:  # MODIFIER_ADD
                continue
            if not entry.inflictor_name:
                continue
            if not RuneType.is_rune_modifier(entry.inflictor_name):
                continue
            if not self._is_hero(entry.target_name):
                continue

            game_time = replay_cache.tick_to_game_time(data, entry.tick)
            hero = self._clean_name(entry.target_name)
            rune = RuneType.from_modifier(entry.inflictor_name)

            pickups.append(RunePickup(
                game_time=round(game_time, 1),
                game_time_str=self._format_game_time(game_time),
                hero=hero,
                rune_type=rune.display_name,
            ))

        return sorted(pickups, key=lambda x: x.game_time)


combat_log_parser = CombatLogParser()
