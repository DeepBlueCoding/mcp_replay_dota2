# Dota 2 Replay Parsing Architecture

## Overview

This document describes the architecture for parsing Dota 2 replay files (.dem) and exposing match analysis via MCP tools. The architecture is split into two distinct layers:

1. **Services Layer**: Business logic for replay parsing and match analysis (no MCP dependencies)
2. **MCP Layer**: Thin wrapper exposing services via MCP tools/resources (no business logic)

This separation allows the services to be reused in other systems (CLI tools, web APIs, etc.) without MCP dependencies.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Two-Layer Architecture](#two-layer-architecture)
3. [Services Layer](#services-layer)
4. [MCP Layer](#mcp-layer)
5. [python-manta v2 Integration](#python-manta-v2-integration)
6. [Data Models](#data-models)
7. [Cache Strategy](#cache-strategy)
8. [Directory Structure](#directory-structure)
9. [Data Flow](#data-flow)
10. [First Parse: Complete Data Extraction](#first-parse-complete-data-extraction)

---

## Design Principles

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Separation of Concerns** | Business logic in services, MCP logic in MCP layer |
| **Reusable Services** | Services have zero MCP dependencies, can be used anywhere |
| **Parse Once** | Single `Parser.parse()` call per replay via python-manta v2 |
| **Cache Everything** | Full `ParsedReplayData` stored persistently |
| **Thin MCP Layer** | MCP tools are simple wrappers, no business logic |
| **Data-Driven Logic** | Detection algorithms designed around python-manta v2 data |

### Layer Rules

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MCP LAYER (src/mcp/)                                                   │
│                                                                         │
│  ✓ MCP tool/resource definitions                                       │
│  ✓ Parameter validation for MCP                                        │
│  ✓ Response formatting for MCP                                         │
│  ✗ NO business logic                                                   │
│  ✗ NO direct python-manta calls                                        │
│  ✗ NO direct opendota-sdk calls                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  SERVICES LAYER (src/services/)                                         │
│                                                                         │
│  ✓ All business logic                                                  │
│  ✓ python-manta integration                                            │
│  ✓ opendota-sdk integration                                            │
│  ✓ Caching logic                                                       │
│  ✓ Analysis/detection algorithms                                       │
│  ✗ NO MCP imports                                                      │
│  ✗ NO FastMCP dependencies                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP CLIENTS                                   │
│                  (Claude, other MCP consumers)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP LAYER                                     │
│                        src/mcp/                                         │
│                                                                         │
│   tools/                          resources/                            │
│   ├── match_tools.py              ├── heroes_resource.py               │
│   ├── combat_tools.py             ├── map_resource.py                  │
│   ├── fight_tools.py              └── items_resource.py                │
│   ├── lane_tools.py                                                    │
│   ├── jungle_tools.py             server.py (FastMCP setup)            │
│   ├── objective_tools.py                                               │
│   └── timeline_tools.py                                                │
│                                                                         │
│   Only MCP-specific code: tool definitions, parameter validation,       │
│   response formatting. NO business logic.                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVICES LAYER                                  │
│                        src/services/                                    │
│                                                                         │
│   combat/                         cache/                               │
│   ├── combat_service.py           └── replay_cache.py  (disk cache)    │
│   └── fight_service.py                                                 │
│                                   replay/                              │
│   farming/                        └── replay_service.py  (main entry)  │
│   └── farming_service.py                                               │
│                                                                        │
│   rotation/                       lane/                                │
│   └── rotation_service.py         └── lane_service.py                  │
│                                                                         │
│   models/                                                              │
│   └── replay_data.py                                                   │
│                                                                         │
│   All business logic. Zero MCP dependencies.                            │
│   Can be imported and used by CLI, web API, tests, etc.                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Uses
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL DEPENDENCIES                              │
│                                                                         │
│   python-manta v2                 opendota-sdk                          │
│   ├── Parser class                ├── OpenDotaClient                   │
│   ├── parse() / run()             ├── get_match()                      │
│   ├── Callbacks                   ├── get_player()                     │
│   └── seek() (Phase 3)            └── get_heroes()                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Services Layer

### Core Services

#### ReplayService

Main entry point for replay data. Handles caching and orchestrates parsing.

```python
# src/services/replay/replay_service.py

from python_manta import Parser
from src.utils.replay_cache import replay_cache
from ..models.replay_data import ParsedReplayData
from .analyzers import FightDetector, LaneAnalyzer, JungleAnalyzer

class ReplayService:
    """
    Main service for replay data access.
    Handles parsing, caching, and analysis orchestration.

    NO MCP DEPENDENCIES.
    """

    def __init__(self, cache: ReplayCache):
        self._cache = cache

    def get_parsed_data(self, match_id: int) -> ParsedReplayData:
        """
        Get complete parsed data for a match.
        Returns cached data if available, otherwise parses replay.
        """
        # Check cache
        cached = self._cache.get(match_id)
        if cached:
            return cached

        # Download and parse
        replay_path = self._download_replay(match_id)
        data = self._parse_replay(replay_path, match_id)

        # Cache and return
        self._cache.set(match_id, data)
        return data

    def _parse_replay(self, path: str, match_id: int) -> ParsedReplayData:
        """Single-pass parse using python-manta v2."""

        parser = Parser(path)

        # Single parse, all data
        result = parser.parse(
            header=True,
            game_info=True,
            combat_log={
                "types": [0, 1, 2, 3, 4, 5, 6, 11, 13],
                "max": 100000,
            },
            entities={
                "interval": 900,
                "classes": ["Hero", "Building", "Creep", "NeutralCreep", "Ward"],
            },
            game_events=True,
            modifiers=True,
        )

        # Run analyzers on raw data
        fights, kills = FightDetector().analyze(
            result.combat_log.entries,
            result.entities.snapshots
        )

        lane_states, aggro_events = LaneAnalyzer().analyze(
            result.entities.snapshots,
            result.combat_log.entries
        )

        camp_pulls, camp_stacks = JungleAnalyzer().analyze(
            result.entities.snapshots,
            result.game_events.events
        )

        # Build complete data model
        return ParsedReplayData(
            match_id=match_id,
            header=result.header,
            game_info=result.game_info,
            combat_log=result.combat_log.entries,
            entity_snapshots=result.entities.snapshots,
            game_events=result.game_events.events,
            modifiers=result.modifiers.events,
            fights=fights,
            kills=kills,
            lane_states=lane_states,
            creep_aggro_events=aggro_events,
            camp_pulls=camp_pulls,
            camp_stacks=camp_stacks,
        )
```

#### CombatService

Provides combat-related queries from parsed data.

```python
# src/services/replay/combat_service.py

from typing import List, Optional
from ..models.combat import Kill, CombatLogEntry
from ..models.replay_data import ParsedReplayData

class CombatService:
    """
    Service for combat data queries.
    Operates on ParsedReplayData, no direct parsing.

    NO MCP DEPENDENCIES.
    """

    def get_kills(
        self,
        data: ParsedReplayData,
        hero: Optional[str] = None,
        team: Optional[str] = None,
    ) -> List[Kill]:
        """Get kills, optionally filtered by hero or team."""
        kills = data.kills

        if hero:
            kills = [k for k in kills if k.killer == hero or k.victim == hero]

        if team:
            team_id = 2 if team == "radiant" else 3
            kills = [k for k in kills if k.killer_team == team_id]

        return kills

    def get_hero_deaths(
        self,
        data: ParsedReplayData,
        hero: Optional[str] = None,
    ) -> List[Kill]:
        """Get hero deaths."""
        deaths = data.kills

        if hero:
            deaths = [k for k in deaths if k.victim == hero]

        return deaths

    def get_damage_breakdown(
        self,
        data: ParsedReplayData,
        kill_id: str,
    ) -> List[CombatLogEntry]:
        """Get damage events leading to a kill."""
        kill = data.get_kill_by_id(kill_id)
        if not kill:
            return []

        # Find damage events in window before death
        window_start = kill.game_time - 10.0
        window_end = kill.game_time

        return [
            e for e in data.combat_log
            if e.type == 0  # DAMAGE
            and e.target_name == kill.victim
            and window_start <= e.game_time <= window_end
        ]
```

#### FightService

Provides fight-related queries.

```python
# src/services/replay/fight_service.py

from typing import List, Optional
from ..models.fights import Fight, Kill
from ..models.replay_data import ParsedReplayData

class FightService:
    """
    Service for fight data queries.

    NO MCP DEPENDENCIES.
    """

    def list_fights(self, data: ParsedReplayData) -> List[Fight]:
        """Get all fights in the match."""
        return data.fights

    def get_fight(self, data: ParsedReplayData, fight_id: str) -> Optional[Fight]:
        """Get a specific fight by ID."""
        return data.get_fight_by_id(fight_id)

    def get_fight_kills(self, data: ParsedReplayData, fight_id: str) -> List[Kill]:
        """Get all kills in a specific fight."""
        return data.get_kills_for_fight(fight_id)

    def get_teamfights(self, data: ParsedReplayData, min_kills: int = 3) -> List[Fight]:
        """Get fights with at least min_kills deaths."""
        return [f for f in data.fights if f.radiant_kills + f.dire_kills >= min_kills]
```

#### LaneService

Provides laning phase queries.

```python
# src/services/replay/lane_service.py

from typing import List, Optional
from ..models.lanes import LaneState, CreepAggroEvent
from ..models.replay_data import ParsedReplayData

class LaneService:
    """
    Service for laning phase data.

    NO MCP DEPENDENCIES.
    """

    def get_lane_state(
        self,
        data: ParsedReplayData,
        game_time: float,
        lane: str,
    ) -> Optional[LaneState]:
        """Get lane state at specific time."""
        return data.get_lane_state_at_time(game_time, lane)

    def get_lane_equilibrium_timeline(
        self,
        data: ParsedReplayData,
        lane: str,
        start_time: float = 0,
        end_time: float = 600,  # First 10 minutes
    ) -> List[LaneState]:
        """Get lane equilibrium over time."""
        return [
            s for s in data.lane_states
            if s.lane == lane
            and start_time <= s.game_time <= end_time
        ]

    def get_creep_aggro_events(
        self,
        data: ParsedReplayData,
        hero: Optional[str] = None,
    ) -> List[CreepAggroEvent]:
        """Get creep aggro manipulation events."""
        events = data.creep_aggro_events

        if hero:
            events = [e for e in events if e.hero == hero]

        return events
```

#### JungleService

Provides jungle-related queries.

```python
# src/services/replay/jungle_service.py

from typing import List, Optional
from ..models.jungle import CampPull, CampStack
from ..models.replay_data import ParsedReplayData

class JungleService:
    """
    Service for jungle data.

    NO MCP DEPENDENCIES.
    """

    def get_camp_stacks(
        self,
        data: ParsedReplayData,
        team: Optional[str] = None,
    ) -> List[CampStack]:
        """Get all camp stacks."""
        stacks = data.camp_stacks

        if team:
            team_id = 2 if team == "radiant" else 3
            stacks = [s for s in stacks if s.stacker_team == team_id]

        return stacks

    def get_camp_pulls(
        self,
        data: ParsedReplayData,
        hero: Optional[str] = None,
    ) -> List[CampPull]:
        """Get all camp pulls."""
        pulls = data.camp_pulls

        if hero:
            pulls = [p for p in pulls if p.puller_hero == hero]

        return pulls
```

### Analyzers

Analyzers process raw data to detect complex events. They run once during parsing.

```python
# src/services/analyzers/fight_detector.py

from typing import List, Tuple
from ..models.fights import Fight, Kill
from ..models.combat import CombatLogEntry
from ..models.entities import EntitySnapshot

class FightDetector:
    """
    Detects and groups fights from combat data.

    NO MCP DEPENDENCIES.
    """

    FIGHT_WINDOW = 15.0  # seconds

    def analyze(
        self,
        combat_log: List[CombatLogEntry],
        entity_snapshots: List[EntitySnapshot],
    ) -> Tuple[List[Fight], List[Kill]]:
        """
        Analyze combat log to detect fights.

        Returns:
            fights: Deduplicated fight objects
            kills: All kills with fight_id references
        """
        # Extract hero deaths
        deaths = [e for e in combat_log if e.type == 4 and self._is_hero(e.target_name)]

        # Group into fights
        fights = []
        kills = []
        current_fight_deaths = []

        for death in sorted(deaths, key=lambda d: d.game_time):
            if not current_fight_deaths:
                current_fight_deaths.append(death)
            elif death.game_time - current_fight_deaths[-1].game_time <= self.FIGHT_WINDOW:
                current_fight_deaths.append(death)
            else:
                # Finalize previous fight
                fight, fight_kills = self._create_fight(current_fight_deaths, combat_log)
                fights.append(fight)
                kills.extend(fight_kills)
                current_fight_deaths = [death]

        # Handle last fight
        if current_fight_deaths:
            fight, fight_kills = self._create_fight(current_fight_deaths, combat_log)
            fights.append(fight)
            kills.extend(fight_kills)

        return fights, kills
```

```python
# src/services/analyzers/lane_analyzer.py

from typing import List, Tuple
from ..models.lanes import LaneState, CreepAggroEvent
from ..models.entities import EntitySnapshot
from ..models.combat import CombatLogEntry

class LaneAnalyzer:
    """
    Analyzes lane equilibrium and creep manipulation.

    NO MCP DEPENDENCIES.
    """

    def analyze(
        self,
        entity_snapshots: List[EntitySnapshot],
        combat_log: List[CombatLogEntry],
    ) -> Tuple[List[LaneState], List[CreepAggroEvent]]:
        """
        Analyze entity snapshots for lane states.

        Returns:
            lane_states: Lane equilibrium at each snapshot
            aggro_events: Detected creep aggro manipulation
        """
        lane_states = []
        aggro_events = []

        for snapshot in entity_snapshots:
            # Only analyze laning phase (first 15 minutes)
            if snapshot.game_time > 900:
                continue

            for lane in ["top", "mid", "bot"]:
                state = self._calculate_lane_state(snapshot, lane)
                lane_states.append(state)

        # Detect aggro manipulation from creep target changes
        aggro_events = self._detect_aggro_events(entity_snapshots)

        return lane_states, aggro_events
```

```python
# src/services/analyzers/jungle_analyzer.py

from typing import List, Tuple
from ..models.jungle import CampPull, CampStack
from ..models.entities import EntitySnapshot
from ..models.events import GameEvent

class JungleAnalyzer:
    """
    Analyzes jungle activity: pulls, stacks.

    NO MCP DEPENDENCIES.
    """

    def analyze(
        self,
        entity_snapshots: List[EntitySnapshot],
        game_events: List[GameEvent],
    ) -> Tuple[List[CampPull], List[CampStack]]:
        """
        Analyze jungle activity.

        Returns:
            pulls: Detected camp pulls
            stacks: Detected camp stacks
        """
        # Detection logic depends on what data python-manta v2 provides
        # May use game events like "dota_camp_stacked" if available
        # Or detect from entity position/state changes

        pulls = self._detect_pulls(entity_snapshots, game_events)
        stacks = self._detect_stacks(entity_snapshots, game_events)

        return pulls, stacks
```

---

## MCP Layer

The MCP layer is a thin wrapper. Each tool:
1. Validates MCP parameters
2. Calls the appropriate service
3. Formats the response for MCP

### Tool Definitions

```python
# src/mcp/tools/combat_tools.py

from fastmcp import FastMCP
from ...services.replay.replay_service import ReplayService
from ...services.replay.combat_service import CombatService

def register_combat_tools(mcp: FastMCP, replay_service: ReplayService):
    """Register combat-related MCP tools."""

    combat_service = CombatService()

    @mcp.tool()
    async def get_hero_deaths(
        match_id: int,
        hero: str | None = None,
    ) -> dict:
        """
        Get hero deaths in a match.

        Args:
            match_id: The match ID
            hero: Optional hero name to filter

        Returns:
            List of hero deaths with killer, position, and context
        """
        # Get parsed data (cached or fresh parse)
        data = await replay_service.get_parsed_data(match_id)

        # Call service (business logic)
        deaths = combat_service.get_hero_deaths(data, hero)

        # Format for MCP response
        return {
            "match_id": match_id,
            "count": len(deaths),
            "deaths": [_format_kill(d) for d in deaths],
        }

    @mcp.tool()
    async def get_kills(
        match_id: int,
        killer: str | None = None,
        team: str | None = None,
    ) -> dict:
        """
        Get kills in a match.

        Args:
            match_id: The match ID
            killer: Optional killer hero name
            team: Optional team filter ("radiant" or "dire")
        """
        data = await replay_service.get_parsed_data(match_id)
        kills = combat_service.get_kills(data, killer, team)

        return {
            "match_id": match_id,
            "count": len(kills),
            "kills": [_format_kill(k) for k in kills],
        }


def _format_kill(kill) -> dict:
    """Format a Kill object for MCP response."""
    return {
        "kill_id": kill.kill_id,
        "fight_id": kill.fight_id,
        "game_time": kill.game_time,
        "game_time_str": _format_time(kill.game_time),
        "victim": kill.victim,
        "killer": kill.killer,
        "assisters": kill.assisters,
        "position": {"x": kill.position.x, "y": kill.position.y},
        "is_teamfight": kill.is_teamfight_kill,
    }
```

```python
# src/mcp/tools/fight_tools.py

from fastmcp import FastMCP
from ...services.replay.replay_service import ReplayService
from ...services.replay.fight_service import FightService

def register_fight_tools(mcp: FastMCP, replay_service: ReplayService):
    """Register fight-related MCP tools."""

    fight_service = FightService()

    @mcp.tool()
    async def list_fights(match_id: int) -> dict:
        """
        List all fights in a match.

        Args:
            match_id: The match ID

        Returns:
            List of fights with participants, outcome, and kill references
        """
        data = await replay_service.get_parsed_data(match_id)
        fights = fight_service.list_fights(data)

        return {
            "match_id": match_id,
            "count": len(fights),
            "fights": [_format_fight_summary(f) for f in fights],
        }

    @mcp.tool()
    async def get_fight(match_id: int, fight_id: str) -> dict:
        """
        Get details of a specific fight.

        Args:
            match_id: The match ID
            fight_id: The fight ID (from list_fights)
        """
        data = await replay_service.get_parsed_data(match_id)
        fight = fight_service.get_fight(data, fight_id)

        if not fight:
            return {"error": f"Fight {fight_id} not found"}

        kills = fight_service.get_fight_kills(data, fight_id)

        return {
            "match_id": match_id,
            "fight": _format_fight_detail(fight),
            "kills": [_format_kill(k) for k in kills],
        }

    @mcp.tool()
    async def get_teamfights(match_id: int, min_kills: int = 3) -> dict:
        """
        Get major teamfights (3+ kills by default).

        Args:
            match_id: The match ID
            min_kills: Minimum kills to qualify as teamfight
        """
        data = await replay_service.get_parsed_data(match_id)
        fights = fight_service.get_teamfights(data, min_kills)

        return {
            "match_id": match_id,
            "min_kills": min_kills,
            "count": len(fights),
            "teamfights": [_format_fight_summary(f) for f in fights],
        }
```

```python
# src/mcp/tools/lane_tools.py

from fastmcp import FastMCP
from ...services.replay.replay_service import ReplayService
from ...services.replay.lane_service import LaneService

def register_lane_tools(mcp: FastMCP, replay_service: ReplayService):
    """Register laning phase MCP tools."""

    lane_service = LaneService()

    @mcp.tool()
    async def get_lane_equilibrium(
        match_id: int,
        lane: str,
        minute: int,
    ) -> dict:
        """
        Get lane equilibrium at a specific minute.

        Args:
            match_id: The match ID
            lane: Lane name ("top", "mid", "bot")
            minute: Game minute
        """
        data = await replay_service.get_parsed_data(match_id)
        state = lane_service.get_lane_state(data, minute * 60.0, lane)

        if not state:
            return {"error": f"No lane data at minute {minute}"}

        return {
            "match_id": match_id,
            "lane": lane,
            "minute": minute,
            "state": _format_lane_state(state),
        }

    @mcp.tool()
    async def get_creep_aggro_events(
        match_id: int,
        hero: str | None = None,
    ) -> dict:
        """
        Get creep aggro manipulation events.

        Args:
            match_id: The match ID
            hero: Optional hero name to filter
        """
        data = await replay_service.get_parsed_data(match_id)
        events = lane_service.get_creep_aggro_events(data, hero)

        return {
            "match_id": match_id,
            "count": len(events),
            "events": [_format_aggro_event(e) for e in events],
        }
```

```python
# src/mcp/tools/jungle_tools.py

from fastmcp import FastMCP
from ...services.replay.replay_service import ReplayService
from ...services.replay.jungle_service import JungleService

def register_jungle_tools(mcp: FastMCP, replay_service: ReplayService):
    """Register jungle MCP tools."""

    jungle_service = JungleService()

    @mcp.tool()
    async def get_camp_stacks(
        match_id: int,
        team: str | None = None,
    ) -> dict:
        """
        Get camp stacking events.

        Args:
            match_id: The match ID
            team: Optional team filter ("radiant" or "dire")
        """
        data = await replay_service.get_parsed_data(match_id)
        stacks = jungle_service.get_camp_stacks(data, team)

        return {
            "match_id": match_id,
            "count": len(stacks),
            "stacks": [_format_camp_stack(s) for s in stacks],
        }

    @mcp.tool()
    async def get_camp_pulls(
        match_id: int,
        hero: str | None = None,
    ) -> dict:
        """
        Get camp pull events.

        Args:
            match_id: The match ID
            hero: Optional hero name to filter
        """
        data = await replay_service.get_parsed_data(match_id)
        pulls = jungle_service.get_camp_pulls(data, hero)

        return {
            "match_id": match_id,
            "count": len(pulls),
            "pulls": [_format_camp_pull(p) for p in pulls],
        }
```

### MCP Server Setup

```python
# src/mcp/server.py

from fastmcp import FastMCP
from ..services.replay.replay_service import ReplayService
from ..services.cache.replay_cache import ReplayCache
from .tools.combat_tools import register_combat_tools
from .tools.fight_tools import register_fight_tools
from .tools.lane_tools import register_lane_tools
from .tools.jungle_tools import register_jungle_tools
from .tools.match_tools import register_match_tools
from .tools.objective_tools import register_objective_tools
from .tools.timeline_tools import register_timeline_tools
from .resources.heroes_resource import register_heroes_resources
from .resources.map_resource import register_map_resources

def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server."""

    mcp = FastMCP("Dota 2 Match Analysis")

    # Initialize services (shared across tools)
    cache = ReplayCache()
    replay_service = ReplayService(cache)

    # Register all tools
    register_match_tools(mcp, replay_service)
    register_combat_tools(mcp, replay_service)
    register_fight_tools(mcp, replay_service)
    register_lane_tools(mcp, replay_service)
    register_jungle_tools(mcp, replay_service)
    register_objective_tools(mcp, replay_service)
    register_timeline_tools(mcp, replay_service)

    # Register resources
    register_heroes_resources(mcp)
    register_map_resources(mcp)

    return mcp

# Entry point
mcp = create_mcp_server()
```

---

## python-manta v2 Integration

The services layer uses python-manta v2's single-pass API:

### Batch Mode (Primary)

```python
from python_manta import Parser

parser = Parser(replay_path)

# Single parse, all data types
result = parser.parse(
    header=True,
    game_info=True,
    combat_log={
        "types": [0, 1, 2, 3, 4, 5, 6, 11, 13],
        "max": 100000,
    },
    entities={
        "interval": 900,  # 30-second snapshots
        "classes": ["Hero", "Building", "Creep", "NeutralCreep", "Ward"],
    },
    game_events=True,
    modifiers=True,
)

# All data available from single parse
result.header.map_name
result.game_info.match_id
result.combat_log.entries
result.entities.snapshots
result.game_events.events
result.modifiers.events
```

### Callback Mode (Alternative)

```python
from python_manta import Parser

parser = Parser(replay_path)

# Register callbacks
@parser.on_combat_log
def handle_combat(entry):
    accumulator.add(entry)

@parser.on_entity(class_filter=["Hero", "Creep"])
def handle_entity(entity, tick):
    tracker.update(entity, tick)

# Single parse, callbacks fire
parser.run()
```

### Dense Seek (Phase 3)

For detailed fight analysis:

```python
# Build index once
parser = Parser(replay_path)
parser.build_index()

# Seek to specific range
parser.seek(tick=45000)
dense_result = parser.parse(
    start_tick=45000,
    end_tick=46000,
    entities={"interval": 1},  # Every tick
)
```

---

## Data Models

All models are Pydantic classes in `src/services/models/`.

```python
# src/services/models/replay_data.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class ParsedReplayData:
    """Complete extraction from a replay file."""

    # Metadata
    match_id: int
    parse_timestamp: float
    parser_version: str

    # From python-manta v2
    header: HeaderInfo
    game_info: GameInfo
    combat_log: List[CombatLogEntry]
    entity_snapshots: List[EntitySnapshot]
    game_events: List[GameEvent]
    modifiers: List[ModifierEvent]

    # Indexed data
    hero_positions: Dict[int, Dict[str, Position]]
    tick_time_map: List[Tuple[int, float]]

    # Derived data (from analyzers)
    fights: List[Fight]
    kills: List[Kill]
    lane_states: List[LaneState]
    creep_aggro_events: List[CreepAggroEvent]
    camp_pulls: List[CampPull]
    camp_stacks: List[CampStack]
    objectives: List[ObjectiveEvent]
    ward_events: List[WardEvent]

    # Indexes for fast lookup
    _fight_index: Dict[str, Fight] = None
    _kill_index: Dict[str, Kill] = None

    def get_fight_by_id(self, fight_id: str) -> Optional[Fight]:
        if self._fight_index is None:
            self._fight_index = {f.fight_id: f for f in self.fights}
        return self._fight_index.get(fight_id)

    def get_kill_by_id(self, kill_id: str) -> Optional[Kill]:
        if self._kill_index is None:
            self._kill_index = {k.kill_id: k for k in self.kills}
        return self._kill_index.get(kill_id)

    def get_kills_for_fight(self, fight_id: str) -> List[Kill]:
        return [k for k in self.kills if k.fight_id == fight_id]

    def get_lane_state_at_time(self, game_time: float, lane: str) -> Optional[LaneState]:
        # Find nearest snapshot
        for state in self.lane_states:
            if state.lane == lane and abs(state.game_time - game_time) < 30:
                return state
        return None
```

---

## Cache Strategy

```python
# src/utils/replay_cache.py

from pathlib import Path
from diskcache import Cache
from dataclasses import dataclass

class ReplayCache:
    """
    Disk-based cache for parsed replay data.

    NO MCP DEPENDENCIES.
    """

    CACHE_DIR = Path.home() / ".cache/mcp_dota2/parsed_replays"
    PRIMARY_TTL = 604800  # 7 days
    SIZE_LIMIT = 5 * 1024**3  # 5 GB

    def __init__(self):
        self._cache = Cache(
            directory=str(self.CACHE_DIR),
            size_limit=self.SIZE_LIMIT,
        )

    def get(self, match_id: int) -> Optional[ParsedReplayData]:
        """Get cached data if available."""
        key = f"replay_{match_id}"
        data = self._cache.get(key)
        if data:
            self._cache.touch(key, expire=self.PRIMARY_TTL)
            return self._deserialize(data)
        return None

    def set(self, match_id: int, data: ParsedReplayData) -> None:
        """Cache parsed data."""
        key = f"replay_{match_id}"
        self._cache.set(key, self._serialize(data), expire=self.PRIMARY_TTL)

    def clear_expired(self) -> int:
        """Remove expired entries."""
        return self._cache.expire()
```

---

## Directory Structure

```
src/
├── mcp/                              # MCP Layer (thin wrapper)
│   ├── __init__.py
│   ├── server.py                     # FastMCP setup, tool registration
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── match_tools.py            # get_match_info, get_draft, etc.
│   │   ├── combat_tools.py           # get_kills, get_hero_deaths, etc.
│   │   ├── fight_tools.py            # list_fights, get_fight, etc.
│   │   ├── lane_tools.py             # get_lane_equilibrium, get_aggro_events
│   │   ├── jungle_tools.py           # get_camp_stacks, get_camp_pulls
│   │   ├── objective_tools.py        # get_roshan_kills, get_tower_kills
│   │   └── timeline_tools.py         # get_timeline, get_stats_at_minute
│   └── resources/
│       ├── __init__.py
│       ├── heroes_resource.py        # Hero data resources
│       └── map_resource.py           # Map data resources
│
├── utils/                            # Utilities (helpers)
│   ├── match_fetcher.py              # OpenDota API fetcher
│   ├── timeline_parser.py            # Timeline extraction (uses ParsedReplayData)
│   ├── match_info_parser.py          # Match info extraction (uses ParsedReplayData)
│   └── ...
│
├── services/                         # Services Layer (business logic)
│   ├── __init__.py
│   │
│   ├── cache/                        # Caching layer
│   │   └── replay_cache.py           # Disk-based replay data cache
│   │
│   ├── replay/                       # Replay services
│   │   └── replay_service.py         # Main entry, download + parse + cache
│   │
│   ├── combat/                       # Combat services
│   │   ├── combat_service.py         # Hero deaths, combat log
│   │   └── fight_service.py          # Fight detection
│   │
│   ├── farming/                      # Farming services
│   │   └── farming_service.py        # Farming pattern analysis
│   │
│   ├── lane/                         # Lane services
│   │   └── lane_service.py           # Laning phase analysis
│   │
│   ├── opendota/                     # OpenDota API services
│   │   ├── __init__.py
│   │   ├── match_service.py          # Match data from API
│   │   ├── player_service.py         # Player data
│   │   └── hero_service.py           # Hero metadata
│   │
│   ├── analyzers/                    # Post-parse analyzers
│   │   ├── __init__.py
│   │   ├── fight_detector.py         # Fight detection
│   │   ├── lane_analyzer.py          # Lane equilibrium
│   │   ├── jungle_analyzer.py        # Pulls, stacks
│   │   ├── objective_analyzer.py     # Roshan, towers
│   │   └── vision_analyzer.py        # Wards, smokes
│   │
│   └── models/                       # Data models (Pydantic)
│       ├── __init__.py
│       ├── replay_data.py            # ParsedReplayData
│       ├── combat.py                 # CombatLogEntry, DamageSource
│       ├── fights.py                 # Fight, Kill
│       ├── lanes.py                  # LaneState, CreepAggroEvent
│       ├── jungle.py                 # CampPull, CampStack
│       ├── objectives.py             # ObjectiveEvent
│       ├── vision.py                 # WardEvent, SmokeEvent
│       ├── entities.py               # EntitySnapshot, HeroState
│       └── common.py                 # Position, TimeRange, etc.
│
└── __init__.py

# Entry point
dota_match_mcp_server.py              # Imports and runs src/mcp/server.py
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MCP Client calls: get_fight(match_id=123, fight_id="fight_45000")     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  MCP LAYER: src/mcp/tools/fight_tools.py                               │
│                                                                         │
│  @mcp.tool()                                                           │
│  async def get_fight(match_id: int, fight_id: str):                    │
│      data = await replay_service.get_parsed_data(match_id)  ──────┐    │
│      fight = fight_service.get_fight(data, fight_id)              │    │
│      return _format_fight(fight)                                  │    │
│                                                                   │    │
└───────────────────────────────────────────────────────────────────│────┘
                                                                    │
                                    ┌───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SERVICES LAYER: src/services/replay/replay_service.py                 │
│                                                                         │
│  def get_parsed_data(match_id):                                        │
│      # Check cache                                                     │
│      cached = cache.get(match_id)  ─────────────────────┐              │
│      if cached: return cached                           │              │
│                                                         │              │
│      # Parse with python-manta v2 (single pass)         │              │
│      result = Parser(path).parse(...)                   │              │
│                                                         │              │
│      # Run analyzers                                    │              │
│      fights, kills = FightDetector().analyze(...)       │              │
│      lane_states = LaneAnalyzer().analyze(...)          │              │
│                                                         │              │
│      # Cache and return                                 │              │
│      cache.set(match_id, data)                          │              │
│      return data                                        │              │
│                                            ┌────────────┘              │
└────────────────────────────────────────────│───────────────────────────┘
                                             │
                          ┌──────────────────┴──────────────────┐
                          │                                     │
                    CACHE HIT                              CACHE MISS
                          │                                     │
                          ▼                                     ▼
              ┌───────────────────┐              ┌───────────────────────┐
              │  Return cached    │              │  python-manta v2      │
              │  ParsedReplayData │              │  Parser(path).parse() │
              └───────────────────┘              │  Single-pass parsing  │
                                                 └───────────────────────┘
```

---

## First Parse: Complete Data Extraction

During first parse, extract EVERYTHING:

### Raw Data (from python-manta v2)
- [ ] Header info
- [ ] Game info (draft, teams, result)
- [ ] Combat log (all types: damage, heal, death, ability, item, purchase)
- [ ] Entity snapshots (heroes, buildings, creeps, neutrals, wards)
- [ ] Game events (all dota_* events)
- [ ] Modifiers (buffs/debuffs)

### Derived Data (from analyzers)
- [ ] Fights (grouped, deduplicated)
- [ ] Kills (with fight references)
- [ ] Lane states (equilibrium at intervals)
- [ ] Creep aggro events
- [ ] Camp pulls
- [ ] Camp stacks
- [ ] Objective events (Roshan, towers, barracks)
- [ ] Ward events
- [ ] Smoke events

### Indexed Data (for fast lookup)
- [ ] Hero positions by tick
- [ ] Tick ↔ game time mapping
- [ ] Fight index by ID
- [ ] Kill index by ID

---

## Summary

| Layer | Location | Responsibility | Dependencies |
|-------|----------|----------------|--------------|
| **MCP** | `src/mcp/` | Tool definitions, parameter validation, response formatting | FastMCP, Services |
| **Services** | `src/services/` | Business logic, parsing, caching, analysis | python-manta, opendota-sdk |
| **Models** | `src/services/models/` | Data structures (Pydantic) | None |

This separation allows:
- Services can be used in CLI tools, web APIs, tests without MCP
- MCP layer stays thin and focused on MCP concerns
- Easy to add new interfaces (REST API, GraphQL) using same services
