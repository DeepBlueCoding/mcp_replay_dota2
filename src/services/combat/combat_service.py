"""
Combat service for extracting kills, deaths, and damage from parsed replay data.

NO MCP DEPENDENCIES - can be used from any interface.
"""

import logging
from typing import List, Optional

from python_manta import CombatLogType, Team

from ..models.combat_data import (
    DamageEvent,
    HeroDeath,
    ItemPurchase,
    ObjectiveKill,
    RunePickup,
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

    def _clean_hero_name(self, name: str) -> str:
        """Remove npc_dota_hero_ prefix from hero name."""
        if name.startswith("npc_dota_hero_"):
            return name[14:]
        return name

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

            death = HeroDeath(
                game_time=game_time,
                game_time_str=self._format_time(game_time),
                tick=entry.tick,
                killer=killer,
                victim=victim,
                killer_is_hero=entry.is_attacker_hero,
                ability=entry.inflictor_name if entry.inflictor_name else None,
                position_x=entry.location_x if hasattr(entry, 'location_x') else None,
                position_y=entry.location_y if hasattr(entry, 'location_y') else None,
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
                ability=entry.inflictor_name if entry.inflictor_name else None,
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
