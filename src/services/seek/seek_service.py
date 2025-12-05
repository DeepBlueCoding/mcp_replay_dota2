"""
Dense seek service for high-resolution replay analysis.

Uses python-manta v2's snapshot() and parse_range() for tick-level queries.
NO MCP DEPENDENCIES.
"""

import logging
from typing import Dict, List, Optional

from python_manta import Parser, Team
from python_manta.manta_python import EntityStateSnapshot
from python_manta.manta_python import HeroSnapshot as MantaHeroSnapshot

from ..models.seek_data import (
    FightReplay,
    GameSnapshot,
    HeroSnapshot,
    PositionTimeline,
)

logger = logging.getLogger(__name__)

# Dota 2 tick rate: ~30 ticks per second
TICKS_PER_SECOND = 30


class SeekService:
    """
    Service for high-resolution replay analysis.

    Provides:
    - Game state snapshots at specific ticks/times
    - Position timelines for heroes
    - Fight replays with dense sampling
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

    def _time_to_tick(self, game_time: float) -> int:
        """Convert game time (seconds) to approximate tick."""
        return int(game_time * TICKS_PER_SECOND)

    def _manta_hero_to_snapshot(self, hero: MantaHeroSnapshot) -> HeroSnapshot:
        """Convert python-manta HeroSnapshot to our model."""
        return HeroSnapshot(
            hero=self._clean_hero_name(hero.hero_name),
            team="radiant" if hero.team == Team.RADIANT.value else "dire",
            player_id=hero.player_id,
            x=hero.x,
            y=hero.y,
            health=hero.health,
            max_health=hero.max_health,
            mana=int(hero.mana),
            max_mana=int(hero.max_mana),
            level=hero.level,
            alive=hero.is_alive,
        )

    def get_snapshot_at_tick(
        self,
        replay_path: str,
        tick: int,
    ) -> Optional[GameSnapshot]:
        """
        Get game state at a specific tick.

        Args:
            replay_path: Path to the .dem replay file
            tick: Target tick number

        Returns:
            GameSnapshot with hero positions and states, or None on error
        """
        parser = Parser(replay_path)
        result: EntityStateSnapshot = parser.snapshot(tick, include_illusions=False)

        if not result.success:
            logger.warning(f"Snapshot at tick {tick} failed: {result.error}")
            return None

        heroes = [
            self._manta_hero_to_snapshot(h)
            for h in result.heroes
            if not h.is_illusion and not h.is_clone
        ]

        # Calculate team totals
        radiant_heroes = [h for h in heroes if h.team == "radiant"]
        dire_heroes = [h for h in heroes if h.team == "dire"]

        return GameSnapshot(
            tick=result.tick,
            game_time=result.game_time,
            game_time_str=self._format_time(result.game_time),
            heroes=heroes,
            radiant_gold=sum(h.gold for h in radiant_heroes),
            dire_gold=sum(h.gold for h in dire_heroes),
        )

    def get_snapshot_at_time(
        self,
        replay_path: str,
        game_time: float,
    ) -> Optional[GameSnapshot]:
        """
        Get game state at a specific game time.

        Args:
            replay_path: Path to the .dem replay file
            game_time: Target game time in seconds

        Returns:
            GameSnapshot with hero positions and states, or None on error
        """
        tick = self._time_to_tick(game_time)
        return self.get_snapshot_at_tick(replay_path, tick)

    def get_position_timeline(
        self,
        replay_path: str,
        start_time: float,
        end_time: float,
        hero_filter: Optional[str] = None,
        interval_seconds: float = 1.0,
    ) -> List[PositionTimeline]:
        """
        Get hero positions over a time range at regular intervals.

        Args:
            replay_path: Path to the .dem replay file
            start_time: Start time in seconds
            end_time: End time in seconds
            hero_filter: Only include this hero (optional)
            interval_seconds: Sampling interval in seconds (default 1.0)

        Returns:
            List of PositionTimeline, one per hero
        """
        parser = Parser(replay_path)
        interval_ticks = int(interval_seconds * TICKS_PER_SECOND)

        start_tick = self._time_to_tick(start_time)
        end_tick = self._time_to_tick(end_time)

        # Collect positions at each sample point
        hero_positions: Dict[str, List[tuple]] = {}

        current_tick = start_tick
        while current_tick <= end_tick:
            result = parser.snapshot(current_tick, include_illusions=False)

            if result.success:
                for h in result.heroes:
                    if h.is_illusion or h.is_clone:
                        continue

                    hero_name = self._clean_hero_name(h.hero_name)
                    if hero_filter and hero_filter.lower() not in hero_name.lower():
                        continue

                    if hero_name not in hero_positions:
                        hero_positions[hero_name] = []

                    hero_positions[hero_name].append((
                        result.tick,
                        result.game_time,
                        h.x,
                        h.y,
                    ))

            current_tick += interval_ticks

        # Build timeline objects
        timelines = []
        for hero_name, positions in hero_positions.items():
            # Determine team from first snapshot
            team = "unknown"
            result = parser.snapshot(start_tick, include_illusions=False)
            if result.success:
                for h in result.heroes:
                    if self._clean_hero_name(h.hero_name) == hero_name:
                        team = "radiant" if h.team == Team.RADIANT.value else "dire"
                        break

            timelines.append(PositionTimeline(
                hero=hero_name,
                team=team,
                positions=positions,
            ))

        return timelines

    def get_fight_replay(
        self,
        replay_path: str,
        start_time: float,
        end_time: float,
        interval_seconds: float = 0.5,
    ) -> FightReplay:
        """
        Get high-resolution data for a fight.

        Samples game state at regular intervals during the fight.

        Args:
            replay_path: Path to the .dem replay file
            start_time: Fight start time in seconds
            end_time: Fight end time in seconds
            interval_seconds: Sampling interval (default 0.5s for 2 samples/second)

        Returns:
            FightReplay with snapshots during the fight
        """
        interval_ticks = int(interval_seconds * TICKS_PER_SECOND)

        start_tick = self._time_to_tick(start_time)
        end_tick = self._time_to_tick(end_time)

        snapshots = []
        current_tick = start_tick

        while current_tick <= end_tick:
            snapshot = self.get_snapshot_at_tick(replay_path, current_tick)
            if snapshot:
                snapshots.append(snapshot)
            current_tick += interval_ticks

        return FightReplay(
            start_tick=start_tick,
            end_tick=end_tick,
            start_time=start_time,
            end_time=end_time,
            start_time_str=self._format_time(start_time),
            end_time_str=self._format_time(end_time),
            snapshots=snapshots,
        )

    def get_hero_movement_during_fight(
        self,
        replay_path: str,
        start_time: float,
        end_time: float,
        hero: str,
        interval_seconds: float = 0.2,
    ) -> Optional[PositionTimeline]:
        """
        Get detailed movement data for a hero during a fight.

        Higher resolution than get_position_timeline for detailed analysis.

        Args:
            replay_path: Path to the .dem replay file
            start_time: Fight start time in seconds
            end_time: Fight end time in seconds
            hero: Hero name to track
            interval_seconds: Sampling interval (default 0.2s for 5 samples/second)

        Returns:
            PositionTimeline for the hero, or None if hero not found
        """
        timelines = self.get_position_timeline(
            replay_path=replay_path,
            start_time=start_time,
            end_time=end_time,
            hero_filter=hero,
            interval_seconds=interval_seconds,
        )

        if not timelines:
            return None

        return timelines[0]
