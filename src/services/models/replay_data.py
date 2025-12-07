"""
Data models for parsed replay data.

Wraps python-manta v2 ParseResult with additional derived data.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from python_manta import (
    CombatLogEntry,
    CombatLogResult,
    DemoIndex,
    EntityParseResult,
    EntitySnapshot,
    GameEventsResult,
    GameInfo,
    HeaderInfo,
    ModifiersResult,
    ParseResult,
    Team,
)


class ProgressCallback(Protocol):
    """Protocol for progress reporting callbacks."""

    async def __call__(self, current: int, total: int, message: str) -> None:
        """Report progress.

        Args:
            current: Current progress value (0-100)
            total: Total progress value (always 100)
            message: Human-readable progress message
        """
        ...


@dataclass
class ParsedReplayData:
    """
    Complete parsed data from a replay file.

    Wraps python-manta v2 ParseResult with:
    - Raw data from single-pass parse
    - Derived/analyzed data (fights, lane states, etc.)
    - Index for seeking (optional)
    """

    # Metadata
    match_id: int
    replay_path: str
    parse_version: str = "2.0"

    # Raw data from python-manta v2
    header: Optional[HeaderInfo] = None
    game_info: Optional[GameInfo] = None
    combat_log: Optional[CombatLogResult] = None
    entities: Optional[EntityParseResult] = None
    game_events: Optional[GameEventsResult] = None
    modifiers: Optional[ModifiersResult] = None

    # Metadata from CDOTAMatchMetadataFile (for timeline data)
    metadata: Optional[Dict[str, Any]] = None

    # Index for seeking (built on first parse)
    demo_index: Optional[DemoIndex] = None

    # Convenience accessors
    @property
    def combat_log_entries(self) -> List[CombatLogEntry]:
        """Get combat log entries."""
        if self.combat_log and self.combat_log.entries:
            return self.combat_log.entries
        return []

    @property
    def entity_snapshots(self) -> List[EntitySnapshot]:
        """Get entity snapshots."""
        if self.entities and self.entities.snapshots:
            return self.entities.snapshots
        return []

    @property
    def winner(self) -> Optional[str]:
        """Get match winner (radiant/dire)."""
        if self.game_info:
            return "radiant" if self.game_info.game_winner == Team.RADIANT.value else "dire"
        return None

    @property
    def duration_seconds(self) -> float:
        """Get match duration in seconds (actual game time, not playback time)."""
        # Use max game_time from combat log (playback_time includes draft/pregame)
        if self.combat_log and self.combat_log.entries:
            return max(e.game_time for e in self.combat_log.entries)
        if self.game_info:
            return self.game_info.playback_time
        return 0.0

    @property
    def is_pro_match(self) -> bool:
        """Check if this is a professional match."""
        if self.game_info:
            return self.game_info.is_pro_match()
        return False

    def get_hero_deaths(self) -> List[CombatLogEntry]:
        """Get all hero death events."""
        from python_manta import CombatLogType

        return [
            e for e in self.combat_log_entries
            if e.type == CombatLogType.DEATH.value
            and e.is_target_hero
        ]

    def get_kills_in_time_range(
        self, start_time: float, end_time: float
    ) -> List[CombatLogEntry]:
        """Get hero deaths in a time range."""
        return [
            e for e in self.get_hero_deaths()
            if start_time <= e.game_time <= end_time
        ]

    def to_cache_dict(self) -> Dict[str, Any]:
        """Serialize for cache storage."""
        return {
            "match_id": self.match_id,
            "replay_path": self.replay_path,
            "parse_version": self.parse_version,
            "header": self.header.model_dump() if self.header else None,
            "game_info": self.game_info.model_dump() if self.game_info else None,
            "combat_log": self.combat_log.model_dump() if self.combat_log else None,
            "entities": self.entities.model_dump() if self.entities else None,
            "game_events": self.game_events.model_dump() if self.game_events else None,
            "modifiers": self.modifiers.model_dump() if self.modifiers else None,
            "metadata": self.metadata,
            "demo_index": self.demo_index.model_dump() if self.demo_index else None,
        }

    @classmethod
    def from_cache_dict(cls, data: Dict[str, Any]) -> "ParsedReplayData":
        """Deserialize from cache storage."""
        return cls(
            match_id=data["match_id"],
            replay_path=data["replay_path"],
            parse_version=data.get("parse_version", "2.0"),
            header=HeaderInfo(**data["header"]) if data.get("header") else None,
            game_info=GameInfo(**data["game_info"]) if data.get("game_info") else None,
            combat_log=CombatLogResult(**data["combat_log"]) if data.get("combat_log") else None,
            entities=EntityParseResult(**data["entities"]) if data.get("entities") else None,
            game_events=GameEventsResult(**data["game_events"]) if data.get("game_events") else None,
            modifiers=ModifiersResult(**data["modifiers"]) if data.get("modifiers") else None,
            metadata=data.get("metadata"),
            demo_index=DemoIndex(**data["demo_index"]) if data.get("demo_index") else None,
        )

    @classmethod
    def from_parse_result(
        cls,
        match_id: int,
        replay_path: str,
        result: ParseResult,
        metadata: Optional[Dict[str, Any]] = None,
        demo_index: Optional[DemoIndex] = None,
    ) -> "ParsedReplayData":
        """Create from python-manta v2 ParseResult."""
        return cls(
            match_id=match_id,
            replay_path=replay_path,
            header=result.header,
            game_info=result.game_info,
            combat_log=result.combat_log,
            entities=result.entities,
            game_events=result.game_events,
            modifiers=result.modifiers,
            metadata=metadata,
            demo_index=demo_index,
        )
