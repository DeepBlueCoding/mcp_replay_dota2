"""
Replay data cache using diskcache.

Parses replay files ONCE and caches all extracted data for subsequent queries.
This dramatically improves performance by avoiding repeated parsing of 400MB+ files.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from diskcache import Cache
from python_manta import MantaParser

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "mcp_dota2" / "parsed_replays"
DEFAULT_TTL = 86400 * 7  # 7 days
DEFAULT_SIZE_LIMIT = 5 * 1024**3  # 5GB


@dataclass
class CombatLogEntry:
    """Raw combat log entry from replay."""

    tick: int
    type: int
    attacker_name: str
    target_name: str
    target_source_name: str
    inflictor_name: str
    value: int
    value_name: str
    game_time: float
    attacker_team: int
    target_team: int


@dataclass
class EntitySnapshot:
    """Entity state snapshot at a specific tick."""

    tick: int
    game_time: float
    players: List[Dict[str, Any]]


@dataclass
class ParsedReplayData:
    """All parsed data from a replay file."""

    match_id: int
    combat_log: List[CombatLogEntry]
    entity_snapshots: List[EntitySnapshot]
    tick_time_map: List[Tuple[int, float]]
    metadata: Optional[Dict[str, Any]]
    hero_positions: Dict[int, Dict[str, Tuple[float, float]]]  # tick -> hero -> (x, y)


class ReplayCache:
    """
    Caches parsed replay data using diskcache.

    Parses replays once and stores all needed data for subsequent queries.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        size_limit: int = DEFAULT_SIZE_LIMIT,
        ttl: int = DEFAULT_TTL,
    ):
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(
            directory=str(self._cache_dir),
            size_limit=size_limit,
        )
        self._ttl = ttl
        self._parser = MantaParser()

    def _extract_match_id(self, replay_path: Path) -> int:
        """Extract match ID from replay filename."""
        match = re.search(r"(\d{10,})", replay_path.name)
        if match:
            return int(match.group(1))
        return hash(str(replay_path))

    def get_parsed_data(self, replay_path: Path) -> ParsedReplayData:
        """
        Get parsed replay data, from cache if available.

        Args:
            replay_path: Path to the .dem replay file

        Returns:
            ParsedReplayData with all extracted data
        """
        match_id = self._extract_match_id(replay_path)
        cache_key = f"replay_{match_id}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for match {match_id}")
            # LRU behavior: reset TTL on access
            self._cache.touch(cache_key, expire=self._ttl)
            return self._deserialize(cached)

        logger.info(f"Cache miss for match {match_id}, parsing replay...")
        data = self._parse_replay(replay_path, match_id)

        self._cache.set(cache_key, self._serialize(data), expire=self._ttl)
        logger.info(f"Cached parsed data for match {match_id}")

        return data

    def _parse_replay(self, replay_path: Path, match_id: int) -> ParsedReplayData:
        """Parse all needed data from replay file in one pass."""
        replay_str = str(replay_path)

        # 1. Parse combat log (all types we need)
        combat_log = self._parse_combat_log(replay_str)
        logger.info(f"Parsed {len(combat_log)} combat log entries")

        # 2. Parse entity snapshots (for timeline and positions)
        entity_snapshots, tick_time_map, hero_positions = self._parse_entities(replay_str)
        logger.info(f"Parsed {len(entity_snapshots)} entity snapshots")

        # 3. Parse metadata
        metadata = self._parse_metadata(replay_str)

        return ParsedReplayData(
            match_id=match_id,
            combat_log=combat_log,
            entity_snapshots=entity_snapshots,
            tick_time_map=tick_time_map,
            metadata=metadata,
            hero_positions=hero_positions,
        )

    def _parse_combat_log(self, replay_str: str) -> List[CombatLogEntry]:
        """Parse all combat log entries we need."""
        # Types: 0=DAMAGE, 1=HEAL, 2=MODIFIER_ADD, 3=MODIFIER_REMOVE, 4=DEATH,
        #        5=ABILITY, 6=ITEM, 11=PURCHASE, 13=ABILITY_TRIGGER (Lotus Orb reflections)
        result = self._parser.parse_combat_log(
            replay_str,
            types=[0, 1, 2, 3, 4, 5, 6, 11, 13],
            max_entries=100000
        )

        entries = []
        for e in result.entries:
            entries.append(CombatLogEntry(
                tick=e.tick,
                type=e.type,
                attacker_name=e.attacker_name,
                target_name=e.target_name,
                target_source_name=getattr(e, 'target_source_name', ''),
                inflictor_name=e.inflictor_name,
                value=getattr(e, 'value', 0),
                value_name=getattr(e, 'value_name', ''),
                game_time=getattr(e, 'game_time', 0.0),
                attacker_team=getattr(e, 'attacker_team', 0),
                target_team=getattr(e, 'target_team', 0),
            ))

        return entries

    def _get_hero_name_by_id(self, hero_id: int) -> Optional[str]:
        """Get hero name from hero_id using constants."""
        try:
            from src.utils.constants_fetcher import constants_fetcher
            heroes = constants_fetcher.get_heroes()
            for hero in heroes.values():
                if hero.get('id') == hero_id:
                    name = hero.get('name', '')
                    if name.startswith('npc_dota_hero_'):
                        return name[14:].lower()
                    return name.lower()
        except Exception:
            pass
        return None

    def _parse_entities(
        self, replay_str: str
    ) -> Tuple[List[EntitySnapshot], List[Tuple[int, float]], Dict[int, Dict[str, Tuple[float, float]]]]:
        """Parse entity snapshots for timeline and positions."""
        # Generate target ticks for ~30 second intervals (900 ticks) up to ~60 min game
        # This provides ~120 snapshots covering a typical match
        target_ticks = list(range(0, 120000, 900))

        result = self._parser.parse_entities(replay_str, target_ticks=target_ticks)

        snapshots = []
        tick_time_map = []
        hero_positions: Dict[int, Dict[str, Tuple[float, float]]] = {}

        for snap in result.snapshots:
            # Build tick-time mapping
            if snap.game_time >= 0:
                tick_time_map.append((snap.tick, snap.game_time))

            # Store player data and hero positions
            players = []
            hero_pos_at_tick: Dict[str, Tuple[float, float]] = {}

            for p in snap.players:
                # Extract hero name from full name (e.g., npc_dota_hero_juggernaut -> juggernaut)
                hero_name = p.hero_name
                if hero_name and hero_name.startswith("npc_dota_hero_"):
                    hero_name_clean = hero_name[14:].lower()
                else:
                    hero_name_clean = hero_name.lower() if hero_name else ""

                players.append({
                    "player_id": p.player_id,
                    "hero_id": getattr(p, 'hero_id', 0),
                    "last_hits": p.last_hits,
                    "denies": p.denies,
                    "gold": p.gold,
                    "level": p.level,
                    "position_x": p.position_x,
                    "position_y": p.position_y,
                })

                # Store hero positions by cleaned name
                if hero_name_clean and (p.position_x != 0.0 or p.position_y != 0.0):
                    hero_pos_at_tick[hero_name_clean] = (p.position_x, p.position_y)

            if hero_pos_at_tick:
                hero_positions[snap.tick] = hero_pos_at_tick

            snapshots.append(EntitySnapshot(
                tick=snap.tick,
                game_time=snap.game_time,
                players=players,
            ))

        return snapshots, tick_time_map, hero_positions

    def _parse_metadata(self, replay_str: str) -> Optional[Dict[str, Any]]:
        """Parse match metadata."""
        try:
            result = self._parser.parse_universal(replay_str, 'CDOTAMatchMetadataFile', max_messages=1)
            if result.messages:
                return result.messages[0].data
        except Exception as e:
            logger.warning(f"Failed to parse metadata: {e}")
        return None

    def _serialize(self, data: ParsedReplayData) -> Dict[str, Any]:
        """Serialize ParsedReplayData for cache storage."""
        return {
            "match_id": data.match_id,
            "combat_log": [
                {
                    "tick": e.tick,
                    "type": e.type,
                    "attacker_name": e.attacker_name,
                    "target_name": e.target_name,
                    "target_source_name": e.target_source_name,
                    "inflictor_name": e.inflictor_name,
                    "value": e.value,
                    "value_name": e.value_name,
                    "game_time": e.game_time,
                    "attacker_team": e.attacker_team,
                    "target_team": e.target_team,
                }
                for e in data.combat_log
            ],
            "entity_snapshots": [
                {
                    "tick": s.tick,
                    "game_time": s.game_time,
                    "players": s.players,
                }
                for s in data.entity_snapshots
            ],
            "tick_time_map": data.tick_time_map,
            "metadata": data.metadata,
            "hero_positions": {str(k): v for k, v in data.hero_positions.items()},
        }

    def _deserialize(self, cached: Dict[str, Any]) -> ParsedReplayData:
        """Deserialize cached data to ParsedReplayData."""
        return ParsedReplayData(
            match_id=cached["match_id"],
            combat_log=[
                CombatLogEntry(**e) for e in cached["combat_log"]
            ],
            entity_snapshots=[
                EntitySnapshot(
                    tick=s["tick"],
                    game_time=s["game_time"],
                    players=s["players"],
                )
                for s in cached["entity_snapshots"]
            ],
            tick_time_map=[(t, g) for t, g in cached["tick_time_map"]],
            metadata=cached["metadata"],
            hero_positions={int(k): v for k, v in cached["hero_positions"].items()},
        )

    def get_hero_position_at_tick(
        self, data: ParsedReplayData, hero_name: str, tick: int
    ) -> Optional[Tuple[float, float]]:
        """
        Get hero position at a specific tick using cached data.

        Interpolates between snapshots if exact tick not available.
        """
        hero_lower = hero_name.lower()

        # Find closest snapshot tick
        closest_tick = None
        min_diff = float('inf')
        for snap_tick in data.hero_positions.keys():
            diff = abs(snap_tick - tick)
            if diff < min_diff:
                min_diff = diff
                closest_tick = snap_tick

        if closest_tick is None:
            return None

        positions = data.hero_positions.get(closest_tick, {})
        return positions.get(hero_lower)

    def tick_to_game_time(self, data: ParsedReplayData, tick: int) -> float:
        """Convert tick to game time using cached tick-time map."""
        if not data.tick_time_map:
            return 0.0

        before = None
        after = None

        for t, gt in data.tick_time_map:
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

    def clear_match(self, match_id: int) -> bool:
        """Remove cached data for a specific match."""
        cache_key = f"replay_{match_id}"
        return self._cache.delete(cache_key)

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        return self._cache.expire()

    def clear_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": self._cache.volume(),
            "count": len(self._cache),
            "directory": str(self._cache_dir),
        }


# Singleton instance
replay_cache = ReplayCache()
