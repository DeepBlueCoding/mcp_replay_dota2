"""
Combat service for extracting kills, deaths, and damage from parsed replay data.

NO MCP DEPENDENCIES - can be used from any interface.
"""

import logging
from typing import List, Optional, Tuple

from python_manta import CombatLogType, Team

from ...models.combat_log import (
    AbilityUsage,
    BarracksKill,
    CombatLogEvent,
    CombatLogFilters,
    CombatLogResponse,
    CourierKill,
    CourierKillsResponse,
    FightParticipation,
    HeroCombatAnalysisResponse,
    HeroDeath,
    HeroDeathsResponse,
    ItemPurchase,
    ItemPurchasesResponse,
    ObjectiveKillsResponse,
    RoshanKill,
    RunePickup,
    RunePickupsResponse,
    TormentorKill,
    TowerKill,
)
from ...utils.position_tracker import classify_map_position
from ..models.combat_data import (
    DamageEvent,
    ObjectiveKill,
)
from ..models.replay_data import ParsedReplayData

logger = logging.getLogger(__name__)

RUNE_TYPE_MAP = {
    0: "double_damage",
    1: "haste",
    2: "invisibility",
    3: "regeneration",
    4: "arcane",
    5: "shield",
}


class CombatService:
    """
    Service for querying combat data from parsed replays.

    Extracts and filters:
    - Hero deaths
    - Damage events
    - Item purchases
    - Rune pickups
    - Objective kills
    """

    def _format_time(self, seconds: float) -> str:
        """Format game time as M:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def _get_hero_position_at_time(
        self,
        data: ParsedReplayData,
        hero: str,
        target_time: float,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Get hero position at a specific time from entity snapshots.

        Returns:
            Tuple of (x, y, location_description) or (None, None, None)
        """
        hero_lower = hero.lower()
        best_snapshot = None
        min_diff = float('inf')

        for snapshot in data.entity_snapshots:
            diff = abs(snapshot.game_time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_snapshot = snapshot

        if not best_snapshot or min_diff > 30.0:
            return (None, None, None)

        for hero_snap in best_snapshot.heroes:
            hero_name = hero_snap.hero_name or ""
            if hero_name.startswith("npc_dota_hero_"):
                clean_name = hero_name[14:]
            else:
                clean_name = hero_name

            if hero_lower in clean_name.lower():
                pos = classify_map_position(hero_snap.x, hero_snap.y)
                return (hero_snap.x, hero_snap.y, pos.region)

        return (None, None, None)

    def _clean_hero_name(self, name: str) -> str:
        """Remove npc_dota_hero_ prefix from hero name."""
        if name.startswith("npc_dota_hero_"):
            return name[14:]
        return name

    def _normalize_ability_name(
        self, inflictor_name: Optional[str], attacker_is_hero: bool
    ) -> Optional[str]:
        """
        Normalize ability name for display.

        Converts "dota_unknown" to "attack" for hero autoattacks.
        """
        if not inflictor_name:
            return "attack" if attacker_is_hero else None
        if inflictor_name == "dota_unknown" and attacker_is_hero:
            return "attack"
        return inflictor_name

    def _is_hero(self, name: str) -> bool:
        """Check if a name represents a hero."""
        return name.startswith("npc_dota_hero_")

    def get_hero_deaths(
        self,
        data: ParsedReplayData,
        hero_filter: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[HeroDeath]:
        """
        Get all hero death events from parsed data.

        Args:
            data: ParsedReplayData from ReplayService
            hero_filter: Only include deaths involving this hero (as killer or victim)
            start_time: Filter deaths after this game time
            end_time: Filter deaths before this game time

        Returns:
            List of HeroDeath events sorted by game time
        """
        deaths = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            if not entry.is_target_hero:
                continue

            game_time = entry.game_time
            if start_time is not None and game_time < start_time:
                continue
            if end_time is not None and game_time > end_time:
                continue

            killer = self._clean_hero_name(entry.attacker_name)
            victim = self._clean_hero_name(entry.target_name)

            if hero_filter:
                hero_lower = hero_filter.lower()
                if hero_lower not in killer.lower() and hero_lower not in victim.lower():
                    continue

            # Get victim position from entity snapshots
            pos_x, pos_y, location_desc = self._get_hero_position_at_time(
                data, victim, game_time
            )

            death = HeroDeath(
                game_time=game_time,
                game_time_str=self._format_time(game_time),
                tick=entry.tick,
                killer=killer,
                victim=victim,
                killer_is_hero=entry.is_attacker_hero,
                ability=self._normalize_ability_name(entry.inflictor_name, entry.is_attacker_hero),
                position_x=pos_x,
                position_y=pos_y,
                location_description=location_desc,
            )
            deaths.append(death)

        deaths.sort(key=lambda d: d.game_time)
        return deaths

    def get_damage_events(
        self,
        data: ParsedReplayData,
        hero_filter: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        heroes_only: bool = True,
    ) -> List[DamageEvent]:
        """
        Get damage events from parsed data.

        Args:
            data: ParsedReplayData from ReplayService
            hero_filter: Only include damage involving this hero
            start_time: Filter after this game time
            end_time: Filter before this game time
            heroes_only: Only include hero vs hero damage

        Returns:
            List of DamageEvent sorted by game time
        """
        events = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DAMAGE.value:
                continue

            if heroes_only and not (entry.is_attacker_hero and entry.is_target_hero):
                continue

            game_time = entry.game_time
            if start_time is not None and game_time < start_time:
                continue
            if end_time is not None and game_time > end_time:
                continue

            attacker = self._clean_hero_name(entry.attacker_name)
            target = self._clean_hero_name(entry.target_name)

            if hero_filter:
                hero_lower = hero_filter.lower()
                if hero_lower not in attacker.lower() and hero_lower not in target.lower():
                    continue

            event = DamageEvent(
                game_time=game_time,
                tick=entry.tick,
                attacker=attacker,
                target=target,
                damage=entry.value,
                ability=self._normalize_ability_name(entry.inflictor_name, entry.is_attacker_hero),
                attacker_is_hero=entry.is_attacker_hero,
                target_is_hero=entry.is_target_hero,
            )
            events.append(event)

        events.sort(key=lambda e: e.game_time)
        return events

    def get_item_purchases(
        self,
        data: ParsedReplayData,
        hero_filter: Optional[str] = None,
    ) -> List[ItemPurchase]:
        """
        Get item purchase events from parsed data.

        Args:
            data: ParsedReplayData from ReplayService
            hero_filter: Only include purchases by this hero

        Returns:
            List of ItemPurchase events sorted by game time
        """
        purchases = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.PURCHASE.value:
                continue

            hero = self._clean_hero_name(entry.target_name)

            if hero_filter:
                if hero_filter.lower() not in hero.lower():
                    continue

            purchase = ItemPurchase(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                hero=hero,
                item=entry.value_name if entry.value_name else entry.inflictor_name,
            )
            purchases.append(purchase)

        purchases.sort(key=lambda p: p.game_time)
        return purchases

    def get_rune_pickups(
        self,
        data: ParsedReplayData,
        hero_filter: Optional[str] = None,
    ) -> List[RunePickup]:
        """
        Get rune pickup events from parsed data.

        Args:
            data: ParsedReplayData from ReplayService
            hero_filter: Only include pickups by this hero

        Returns:
            List of RunePickup events sorted by game time
        """
        pickups = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.PICKUP_RUNE.value:
                continue

            hero = self._clean_hero_name(entry.target_name)

            if hero_filter:
                if hero_filter.lower() not in hero.lower():
                    continue

            rune_type = RUNE_TYPE_MAP.get(entry.value, f"unknown_{entry.value}")

            pickup = RunePickup(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                hero=hero,
                rune_type=rune_type,
            )
            pickups.append(pickup)

        pickups.sort(key=lambda p: p.game_time)
        return pickups

    def get_roshan_kills(self, data: ParsedReplayData) -> List[ObjectiveKill]:
        """Get Roshan kill events."""
        kills = []
        kill_number = 0

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            if "roshan" not in entry.target_name.lower():
                continue

            kill_number += 1
            killer = self._clean_hero_name(entry.attacker_name)
            team = "radiant" if entry.attacker_team == Team.RADIANT.value else "dire"

            kill = ObjectiveKill(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                objective_type="roshan",
                objective_name=f"Roshan #{kill_number}",
                killer=killer if entry.is_attacker_hero else None,
                team=team,
                extra_info={"kill_number": kill_number},
            )
            kills.append(kill)

        return kills

    def get_tormentor_kills(self, data: ParsedReplayData) -> List[ObjectiveKill]:
        """Get Tormentor kill events."""
        kills = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            target = entry.target_name.lower()
            if "tormentor" not in target:
                continue

            # Determine which side's tormentor was killed (radiant or dire side)
            tormentor_side = "dire" if "badguys" in target else "radiant"
            killer = self._clean_hero_name(entry.attacker_name)
            team = "radiant" if entry.attacker_team == Team.RADIANT.value else "dire"

            kill = ObjectiveKill(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                objective_type="tormentor",
                objective_name=f"Tormentor ({tormentor_side} side)",
                killer=killer if entry.is_attacker_hero else None,
                team=team,
                extra_info={"side": tormentor_side},
            )
            kills.append(kill)

        return kills

    def get_tower_kills(self, data: ParsedReplayData) -> List[ObjectiveKill]:
        """Get tower destruction events."""
        kills = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            target = entry.target_name.lower()
            if "tower" not in target or "badguys" not in target and "goodguys" not in target:
                continue

            # Parse tower info from name
            tower_team = "dire" if "badguys" in target else "radiant"
            destroyed_by = "radiant" if tower_team == "dire" else "dire"

            kill = ObjectiveKill(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                objective_type="tower",
                objective_name=entry.target_name,
                killer=self._clean_hero_name(entry.attacker_name) if entry.is_attacker_hero else None,
                team=destroyed_by,
                extra_info={"tower_team": tower_team},
            )
            kills.append(kill)

        return kills

    def get_barracks_kills(self, data: ParsedReplayData) -> List[ObjectiveKill]:
        """Get barracks destruction events."""
        kills = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            target = entry.target_name.lower()
            if "rax" not in target and "barrack" not in target:
                continue

            rax_team = "dire" if "badguys" in target else "radiant"
            destroyed_by = "radiant" if rax_team == "dire" else "dire"
            rax_type = "melee" if "melee" in target else "ranged"

            kill = ObjectiveKill(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                objective_type="barracks",
                objective_name=entry.target_name,
                killer=self._clean_hero_name(entry.attacker_name) if entry.is_attacker_hero else None,
                team=destroyed_by,
                extra_info={"barracks_team": rax_team, "barracks_type": rax_type},
            )
            kills.append(kill)

        return kills

    def get_courier_kills(self, data: ParsedReplayData) -> List[CourierKill]:
        """Get courier kill events."""
        kills = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
            if entry_type != CombatLogType.DEATH.value:
                continue

            target = entry.target_name.lower()
            if "courier" not in target:
                continue

            # Determine courier owner team
            courier_team = "dire" if "badguys" in target else "radiant"

            # Extract owner from target name (e.g., npc_dota_courier_2 -> player 2)
            owner = "unknown"
            if "_courier_" in target:
                try:
                    parts = target.split("_courier_")
                    if len(parts) > 1 and parts[1].isdigit():
                        owner = f"player_{parts[1]}"
                except (IndexError, ValueError):
                    pass

            killer = self._clean_hero_name(entry.attacker_name)

            # Build position if available
            position = None
            if hasattr(entry, 'location_x') and entry.location_x is not None:
                from ...models.combat_log import MapLocation
                pos_info = classify_map_position(entry.location_x, entry.location_y)
                position = MapLocation(
                    x=entry.location_x,
                    y=entry.location_y,
                    region=pos_info.region,
                    lane=pos_info.lane,
                    location=pos_info.location,
                )

            kill = CourierKill(
                game_time=entry.game_time,
                game_time_str=self._format_time(entry.game_time),
                tick=entry.tick,
                killer=killer,
                killer_is_hero=entry.is_attacker_hero,
                owner=owner,
                team=courier_team,
                position=position,
            )
            kills.append(kill)

        return kills

    def _get_event_type_name(self, entry_type: int) -> str:
        """Get human-readable event type name."""
        type_map = {
            CombatLogType.DAMAGE.value: "DAMAGE",
            CombatLogType.HEAL.value: "HEAL",
            CombatLogType.MODIFIER_ADD.value: "MODIFIER_ADD",
            CombatLogType.MODIFIER_REMOVE.value: "MODIFIER_REMOVE",
            CombatLogType.DEATH.value: "DEATH",
            CombatLogType.ABILITY.value: "ABILITY",
            CombatLogType.ITEM.value: "ITEM",
            CombatLogType.PURCHASE.value: "PURCHASE",
            CombatLogType.BUYBACK.value: "BUYBACK",
        }
        return type_map.get(entry_type, f"UNKNOWN_{entry_type}")

    def _is_significant_event(self, entry_type: int) -> bool:
        """Check if event is 'significant' (ability, death, item, purchase, buyback)."""
        significant_types = {
            CombatLogType.DEATH.value,
            CombatLogType.ABILITY.value,
            CombatLogType.ITEM.value,
            CombatLogType.PURCHASE.value,
            CombatLogType.BUYBACK.value,
        }
        return entry_type in significant_types

    def get_combat_log(
        self,
        data: ParsedReplayData,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        hero_filter: Optional[str] = None,
        significant_only: bool = False,
        types: Optional[List[int]] = None,
    ) -> List[CombatLogEvent]:
        """
        Get filtered combat log events.

        Args:
            data: ParsedReplayData from ReplayService
            start_time: Filter events after this game time
            end_time: Filter events before this game time
            hero_filter: Only include events involving this hero
            significant_only: Only include significant events (abilities, deaths, items)
            types: List of CombatLogType values to include (e.g., [5] for ABILITY)

        Returns:
            List of CombatLogEvent sorted by game time
        """
        events = []

        for entry in data.combat_log_entries:
            entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type

            # Type filter
            if types is not None and entry_type not in types:
                continue

            # Time filter
            game_time = entry.game_time
            if start_time is not None and game_time < start_time:
                continue
            if end_time is not None and game_time > end_time:
                continue

            # Significant only filter
            if significant_only and not self._is_significant_event(entry_type):
                continue

            # For significant events, skip non-hero deaths (creep kills etc.)
            if significant_only and entry_type == CombatLogType.DEATH.value:
                if not entry.is_target_hero:
                    continue

            attacker = self._clean_hero_name(entry.attacker_name)
            target = self._clean_hero_name(entry.target_name)

            # Hero filter
            if hero_filter:
                hero_lower = hero_filter.lower()
                if hero_lower not in attacker.lower() and hero_lower not in target.lower():
                    continue

            # Determine if ability "hit" (for ABILITY events)
            hit = None
            if entry_type == CombatLogType.ABILITY.value:
                hit = entry.is_target_hero if hasattr(entry, 'is_target_hero') else None

            event = CombatLogEvent(
                type=self._get_event_type_name(entry_type),
                game_time=game_time,
                game_time_str=self._format_time(game_time),
                tick=entry.tick,
                attacker=attacker,
                attacker_is_hero=entry.is_attacker_hero,
                target=target,
                target_is_hero=entry.is_target_hero,
                ability=self._normalize_ability_name(entry.inflictor_name, entry.is_attacker_hero),
                value=entry.value if hasattr(entry, 'value') else None,
                hit=hit,
            )
            events.append(event)

        events.sort(key=lambda e: e.game_time)
        return events

    # ============ Response methods (return API Response models) ============

    def get_hero_deaths_response(
        self,
        data: ParsedReplayData,
        match_id: int,
        hero_filter: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> HeroDeathsResponse:
        """Get hero deaths and return API response model."""
        deaths = self.get_hero_deaths(data, hero_filter, start_time, end_time)
        return HeroDeathsResponse(
            success=True,
            match_id=match_id,
            total_deaths=len(deaths),
            deaths=deaths,
        )

    def get_combat_log_response(
        self,
        data: ParsedReplayData,
        match_id: int,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        hero_filter: Optional[str] = None,
        significant_only: bool = False,
    ) -> CombatLogResponse:
        """Get combat log and return API response model."""
        events = self.get_combat_log(
            data,
            start_time=start_time,
            end_time=end_time,
            hero_filter=hero_filter,
            significant_only=significant_only,
        )
        return CombatLogResponse(
            success=True,
            match_id=match_id,
            total_events=len(events),
            filters=CombatLogFilters(
                start_time=start_time,
                end_time=end_time,
                hero_filter=hero_filter,
            ),
            events=events,
        )

    def get_item_purchases_response(
        self,
        data: ParsedReplayData,
        match_id: int,
        hero_filter: Optional[str] = None,
    ) -> ItemPurchasesResponse:
        """Get item purchases and return API response model."""
        purchases = self.get_item_purchases(data, hero_filter=hero_filter)
        return ItemPurchasesResponse(
            success=True,
            match_id=match_id,
            hero_filter=hero_filter,
            total_purchases=len(purchases),
            purchases=purchases,
        )

    def get_rune_pickups_response(
        self,
        data: ParsedReplayData,
        match_id: int,
    ) -> RunePickupsResponse:
        """Get rune pickups and return API response model."""
        pickups = self.get_rune_pickups(data)
        return RunePickupsResponse(
            success=True,
            match_id=match_id,
            total_pickups=len(pickups),
            pickups=pickups,
        )

    def get_courier_kills_response(
        self,
        data: ParsedReplayData,
        match_id: int,
    ) -> CourierKillsResponse:
        """Get courier kills and return API response model."""
        kills = self.get_courier_kills(data)
        return CourierKillsResponse(
            success=True,
            match_id=match_id,
            total_kills=len(kills),
            kills=kills,
        )

    def _parse_tower_info(self, name: str) -> tuple:
        """Parse tower tier and lane from name."""
        name_lower = name.lower()
        tier = 1
        lane = "unknown"
        if "tower1" in name_lower or "t1" in name_lower:
            tier = 1
        elif "tower2" in name_lower or "t2" in name_lower:
            tier = 2
        elif "tower3" in name_lower or "t3" in name_lower:
            tier = 3
        elif "tower4" in name_lower or "t4" in name_lower:
            tier = 4
        if "top" in name_lower:
            lane = "top"
        elif "mid" in name_lower:
            lane = "mid"
        elif "bot" in name_lower:
            lane = "bot"
        elif "tower4" in name_lower or "t4" in name_lower:
            lane = "base"
        return tier, lane

    def get_objective_kills_response(
        self,
        data: ParsedReplayData,
        match_id: int,
    ) -> ObjectiveKillsResponse:
        """Get all objective kills and return API response model."""
        roshan_objs = self.get_roshan_kills(data)
        tormentor_objs = self.get_tormentor_kills(data)
        tower_objs = self.get_tower_kills(data)
        barracks_objs = self.get_barracks_kills(data)

        roshan_kills = [
            RoshanKill(
                game_time=r.game_time,
                game_time_str=r.game_time_str,
                killer=r.killer or "unknown",
                team=r.team or "unknown",
                kill_number=r.extra_info.get("kill_number", 0) if r.extra_info else 0,
            )
            for r in roshan_objs
        ]

        tormentor_kills = [
            TormentorKill(
                game_time=t.game_time,
                game_time_str=t.game_time_str,
                killer=t.killer or "unknown",
                team=t.team or "unknown",
                side=t.extra_info.get("side", "unknown") if t.extra_info else "unknown",
            )
            for t in tormentor_objs
        ]

        tower_kills = []
        for t in tower_objs:
            tier, lane = self._parse_tower_info(t.objective_name)
            tower_team = t.extra_info.get("tower_team", "unknown") if t.extra_info else "unknown"
            tower_kills.append(TowerKill(
                game_time=t.game_time,
                game_time_str=t.game_time_str,
                tower=t.objective_name,
                team=tower_team,
                tier=tier,
                lane=lane,
                killer=t.killer or "unknown",
                killer_is_hero=t.killer is not None,
            ))

        barracks_kills = []
        for b in barracks_objs:
            rax_team = b.extra_info.get("barracks_team", "unknown") if b.extra_info else "unknown"
            rax_type = b.extra_info.get("barracks_type", "unknown") if b.extra_info else "unknown"
            lane = "mid"
            if "top" in b.objective_name.lower():
                lane = "top"
            elif "bot" in b.objective_name.lower():
                lane = "bot"
            barracks_kills.append(BarracksKill(
                game_time=b.game_time,
                game_time_str=b.game_time_str,
                barracks=b.objective_name,
                team=rax_team,
                lane=lane,
                type=rax_type,
                killer=b.killer or "unknown",
                killer_is_hero=b.killer is not None,
            ))

        return ObjectiveKillsResponse(
            success=True,
            match_id=match_id,
            roshan_kills=roshan_kills,
            tormentor_kills=tormentor_kills,
            tower_kills=tower_kills,
            barracks_kills=barracks_kills,
        )

    def get_hero_combat_analysis(
        self,
        data: ParsedReplayData,
        match_id: int,
        hero: str,
        fights: List,
    ) -> HeroCombatAnalysisResponse:
        """
        Analyze a hero's combat involvement across all fights.

        Args:
            data: ParsedReplayData from ReplayService
            match_id: Match ID for response
            hero: Hero name to analyze
            fights: List of Fight objects from FightService

        Returns:
            HeroCombatAnalysisResponse with per-fight and aggregate stats
        """
        hero_lower = hero.lower()
        hero_fights: List[FightParticipation] = []
        total_kills = 0
        total_deaths = 0
        total_assists = 0
        total_teamfights = 0
        overall_ability_stats: dict = {}

        for fight in fights:
            if not any(hero_lower in p.lower() for p in fight.participants):
                continue

            fight_start = fight.start_time - 2.0
            fight_end = fight.end_time + 2.0

            kills = 0
            deaths = 0
            assists = 0
            damage_dealt = 0
            damage_received = 0
            ability_casts: dict = {}
            ability_hits: dict = {}
            heroes_damaged_by_hero: set = set()

            for entry in data.combat_log_entries:
                entry_type = entry.type.value if hasattr(entry.type, 'value') else entry.type
                if entry.game_time < fight_start or entry.game_time > fight_end:
                    continue

                attacker = self._clean_hero_name(entry.attacker_name)
                target = self._clean_hero_name(entry.target_name)
                attacker_lower = attacker.lower()
                target_lower = target.lower()
                is_our_hero_attacker = hero_lower in attacker_lower
                is_our_hero_target = hero_lower in target_lower

                if entry_type == CombatLogType.DEATH.value and entry.is_target_hero:
                    if is_our_hero_attacker:
                        kills += 1
                    elif is_our_hero_target:
                        deaths += 1
                    elif target_lower in heroes_damaged_by_hero:
                        assists += 1

                elif entry_type == CombatLogType.DAMAGE.value:
                    if is_our_hero_attacker and entry.is_target_hero:
                        damage_dealt += entry.value or 0
                        heroes_damaged_by_hero.add(target_lower)
                    elif is_our_hero_target and entry.is_attacker_hero:
                        damage_received += entry.value or 0

                elif entry_type == CombatLogType.ABILITY.value and is_our_hero_attacker:
                    ability = entry.inflictor_name
                    if ability and ability != "dota_unknown":
                        ability_casts[ability] = ability_casts.get(ability, 0) + 1
                        if entry.is_target_hero:
                            ability_hits[ability] = ability_hits.get(ability, 0) + 1

                elif entry_type == CombatLogType.MODIFIER_ADD.value:
                    modifier = entry.inflictor_name
                    if modifier and modifier != "dota_unknown" and entry.is_target_hero:
                        if is_our_hero_attacker or (modifier and hero_lower in modifier.lower()):
                            for tracked_ability in ability_casts.keys():
                                ability_base = tracked_ability.split("_")[-1]
                                if ability_base in modifier.lower():
                                    ability_hits[tracked_ability] = ability_hits.get(tracked_ability, 0) + 1
                                    break

            abilities_used = []
            for ability_name, cast_count in ability_casts.items():
                hits = ability_hits.get(ability_name, 0)
                hit_rate = (hits / cast_count * 100) if cast_count > 0 else 0.0
                abilities_used.append(AbilityUsage(
                    ability=ability_name,
                    total_casts=cast_count,
                    hero_hits=hits,
                    hit_rate=round(hit_rate, 1),
                ))
                overall_ability_stats[ability_name] = overall_ability_stats.get(ability_name, {
                    "casts": 0, "hits": 0
                })
                overall_ability_stats[ability_name]["casts"] += cast_count
                overall_ability_stats[ability_name]["hits"] += hits

            abilities_used.sort(key=lambda a: a.total_casts, reverse=True)

            total_kills += kills
            total_deaths += deaths
            total_assists += assists
            if fight.is_teamfight:
                total_teamfights += 1

            hero_fights.append(FightParticipation(
                fight_id=fight.fight_id,
                fight_start=fight.start_time,
                fight_start_str=fight.start_time_str,
                fight_end=fight.end_time,
                fight_end_str=fight.end_time_str,
                is_teamfight=fight.is_teamfight,
                kills=kills,
                deaths=deaths,
                assists=assists,
                abilities_used=abilities_used,
                damage_dealt=damage_dealt,
                damage_received=damage_received,
            ))

        ability_summary = []
        for ability_name, stats in overall_ability_stats.items():
            hit_rate = (stats["hits"] / stats["casts"] * 100) if stats["casts"] > 0 else 0.0
            ability_summary.append(AbilityUsage(
                ability=ability_name,
                total_casts=stats["casts"],
                hero_hits=stats["hits"],
                hit_rate=round(hit_rate, 1),
            ))
        ability_summary.sort(key=lambda a: a.total_casts, reverse=True)

        return HeroCombatAnalysisResponse(
            success=True,
            match_id=match_id,
            hero=hero,
            total_fights=len(hero_fights),
            total_teamfights=total_teamfights,
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists,
            ability_summary=ability_summary,
            fights=hero_fights,
        )
