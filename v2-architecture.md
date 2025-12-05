# Python Manta v2 Architecture

## Overview

This document describes the redesign of python_manta from a multi-pass parsing architecture to a single-pass, streaming-capable parser with seek support.

---

## Key Principles

### 1. One Parse, All Data
The fundamental problem with v1 is that each `parse_*` method creates a new parser and reads the entire file. If you need 5 different data types, you parse the file 5 times.

**v2 Rule**: Parse the file exactly once, collect all requested data in that single pass.

### 2. Manta-Like Naming
Follow the naming conventions of the upstream manta Go library:
- `Parser` (not `MantaParser`, `DemoParser`, `UnifiedParser`)
- `on_entity`, `on_combat_log` (like manta's `OnEntity`)
- No prefixes like `unified_`, `enriched_`, `enhanced_`

### 3. Pythonic API
- Decorators for callbacks
- Generators for streaming
- Context managers for resource handling
- Type hints everywhere

### 4. No Legacy Support
This is a clean break. The v1 architecture was wrong. No fallbacks, no compatibility layers.

### 5. Preserve Working Code
The parsing logic (callbacks, data extraction, string resolution) already works correctly. Reuse it, don't rewrite it. Only change how it's orchestrated.

### 6. Mirror Manta Structure
File structure should mirror dotabuff/manta for easy comparison and debugging.

---

## Current Architecture (v1) - Problem

```
┌─────────────────────────────────────────────────────────────────┐
│  User Code                                                       │
│                                                                  │
│  parser = MantaParser()                                          │
│  header = parser.parse_header("demo.dem")      → FULL PARSE     │
│  info = parser.parse_game_info("demo.dem")     → FULL PARSE     │
│  combat = parser.parse_combat_log("demo.dem")  → FULL PARSE     │
│  entities = parser.parse_entities("demo.dem")  → FULL PARSE     │
│  messages = parser.parse_universal("demo.dem") → FULL PARSE     │
│                                                                  │
│  5 method calls = 5 complete file parses                        │
│  ~500MB file × 5 = 2.5GB of I/O for one analysis                │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Happens

Each `Run*` function in Go:
1. Opens the file
2. Creates a new `manta.StreamParser`
3. Registers callbacks
4. Calls `parser.Start()` (full parse)
5. Returns result

```go
// Current pattern (repeated for each data type)
func RunCombatLogParse(filePath string, config CombatLogConfig) (*CombatLogResult, error) {
    file, _ := os.Open(filePath)           // Opens file
    parser, _ := manta.NewStreamParser(file) // Creates parser
    // ... register callbacks ...
    parser.Start()                          // FULL PARSE
    return result, nil
}
```

---

## New Architecture (v2) - Solution

```
┌─────────────────────────────────────────────────────────────────┐
│  User Code                                                       │
│                                                                  │
│  parser = Parser("demo.dem")                                     │
│  result = parser.parse(                                          │
│      header=True,                                                │
│      game_info=True,                                             │
│      combat_log={"types": [4], "heroes_only": True},            │
│      entities={"interval": 900},                                 │
│      messages={"filter": "ChatMessage"},                         │
│  )                                                               │
│                                                                  │
│  # Access all results from single parse                          │
│  result.header.map_name                                          │
│  result.game_info.match_id                                       │
│  result.combat_log.entries                                       │
│  result.entities.snapshots                                       │
│  result.messages.items                                           │
│                                                                  │
│  1 method call = 1 parse = all data                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Python Layer                             │
│                                                                  │
│   Parser                                                         │
│   ├── __init__(path)      Create parser for file                │
│   ├── parse(**opts)       Single-pass, return ParseResult       │
│   ├── run()               Execute with registered callbacks      │
│   ├── stream()            Generator yielding events              │
│   ├── seek(tick/time)     Jump to position (requires index)     │
│   ├── snapshot()          Get entity state at current position  │
│   ├── build_index()       Create keyframes for seeking          │
│   │                                                              │
│   │  Callback decorators:                                        │
│   ├── @on_combat_log      Combat log entries                     │
│   ├── @on_entity          Entity updates                         │
│   ├── @on_message         Protocol messages                      │
│   └── @on_game_event      Game events                            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                         CGO Bridge                               │
│                                                                  │
│   parser.go                                                      │
│   ├── Parse(path, config)     Single-pass with config           │
│   ├── Open(path) → handle     Open for streaming                │
│   ├── Next(handle) → event    Get next event                    │
│   ├── Snapshot(handle)        Get entity state                  │
│   ├── Seek(handle, tick)      Jump to tick                      │
│   ├── BuildIndex(handle)      Create keyframes                  │
│   └── Close(handle)           Cleanup                           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                         Manta Library                            │
│                                                                  │
│   github.com/dotabuff/manta                                      │
│   ├── StreamParser            Sequential parsing                 │
│   ├── Callbacks.On*()         Event registration                 │
│   ├── OnEntity()              Entity state changes               │
│   ├── OnGameEvent()           Game events                        │
│   └── LookupStringByIndex()   String table resolution            │
│                                                                  │
│   Note: Manta does NOT support seeking natively.                 │
│   We must build our own keyframe index.                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure (Mirroring Manta)

### Manta Go Library Structure
```
github.com/dotabuff/manta/
├── parser.go           # Parser struct, NewStreamParser, Start, Stop
├── entity.go           # Entity struct and methods
├── callbacks.go        # All callback registrations (204KB!)
├── game_event.go       # GameEvent handling
├── string_table.go     # String table handling
├── modifier.go         # Modifier handling
├── field*.go           # Field handling (decoder, path, reader, state, type)
├── class.go            # Class handling
├── stream.go           # Stream reading
└── dota/               # Protobuf types
```

### Our Wrapper Structure (Mirrors Manta)

```
go_wrapper/
│
│  # Core files (mirror manta naming)
├── parser.go           # Parse(), Open(), Next(), Seek(), Close()
├── entity.go           # Entity snapshot collection
├── callbacks.go        # Callback setup (consolidate existing callbacks_*.go)
├── game_event.go       # Game event collection
├── string_table.go     # String table collection
├── modifier.go         # Modifier collection
├── combat_log.go       # Combat log collection (Dota-specific, no manta equivalent)
├── stream.go           # Handle management for streaming API
├── index.go            # Keyframe indexing for seek (no manta equivalent)
│
│  # Support files
├── types.go            # Shared structs (ParseConfig, ParseResult, etc.)
└── util.go             # Helper functions

src/python_manta/
│
│  # Core files (mirror manta naming)
├── parser.py           # Parser class
├── entity.py           # Entity types and helpers
├── game_event.py       # GameEvent types
├── string_table.py     # StringTable types
├── modifier.py         # Modifier types
├── combat_log.py       # CombatLog types (Dota-specific)
│
│  # Support files
├── types.py            # Shared Pydantic models
├── enums.py            # All enums
└── __init__.py         # Public exports
```

### File Mapping: Manta → Our Wrapper

| Manta File | Our Go Wrapper | Our Python | Purpose |
|------------|---------------|------------|---------|
| `parser.go` | `parser.go` | `parser.py` | Main parser, entry points |
| `entity.go` | `entity.go` | `entity.py` | Entity handling |
| `callbacks.go` | `callbacks.go` | (decorators in parser.py) | Callback registration |
| `game_event.go` | `game_event.go` | `game_event.py` | Game events |
| `string_table.go` | `string_table.go` | `string_table.py` | String tables |
| `modifier.go` | `modifier.go` | `modifier.py` | Modifiers/buffs |
| (none) | `combat_log.go` | `combat_log.py` | Combat log (Dota-specific) |
| (none) | `stream.go` | (in parser.py) | Streaming handle mgmt |
| (none) | `index.go` | (in parser.py) | Seek keyframes |

---

## API Design

### 1. Single-Pass Parsing

```python
from python_manta import Parser, CombatLogType

parser = Parser("match.dem")

# Specify what you want, get everything in one parse
result = parser.parse(
    header=True,
    game_info=True,
    combat_log={
        "types": [CombatLogType.DEATH, CombatLogType.DAMAGE],
        "heroes_only": True,
        "max": 1000,
    },
    entities={
        "interval": 900,  # Every 30 seconds
        "max": 100,
    },
    messages={
        "filter": "ChatMessage",
        "max": 500,
    },
)

# All data available
print(result.header.map_name)
print(result.game_info.match_id)
print(len(result.combat_log.entries))
```

### 2. Callback-Based Streaming

```python
parser = Parser("match.dem")

@parser.on_combat_log
def handle_combat(entry):
    if entry.type == CombatLogType.DEATH:
        print(f"Kill: {entry.attacker_name} → {entry.target_name}")

@parser.on_entity(class_filter="Hero")
def handle_hero(entity, tick):
    print(f"Hero {entity.class_name} at tick {tick}")

@parser.on_message("CDOTAUserMsg_ChatMessage")
def handle_chat(msg):
    print(f"Chat: {msg.data}")

# Run - callbacks fire as data is encountered
parser.run()
```

### 3. Generator Streaming

```python
parser = Parser("match.dem")

for event in parser.stream():
    match event.kind:
        case "combat_log":
            print(event.data.attacker_name)
        case "entity":
            print(event.data.class_name)
        case "message":
            print(event.data)
```

### 4. Seek Support (Phase 3)

```python
parser = Parser("match.dem")
parser.build_index()  # One-time cost, creates keyframes

# Jump to specific tick
parser.seek(tick=50000)
state = parser.snapshot()
print(f"Heroes at tick 50000: {state.players}")

# Jump by game time
parser.seek(time=1200.0)  # 20:00 game time

# Parse specific range
result = parser.parse(
    start_tick=30000,
    end_tick=60000,
    combat_log=True,
)
```

---

## Data Flow

### Single-Pass Parse

```
User calls parser.parse(header=True, combat_log={...}, entities={...})
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Python: Build config JSON    │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  CGO: Parse(path, configJSON) │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Go: Open file ONCE           │
                    │  Go: Create parser ONCE       │
                    └───────────────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────────┐
              │  Register callbacks based on config:        │
              │  ├── if header: OnCDemoFileHeader          │
              │  ├── if game_info: OnCDemoFileInfo         │
              │  ├── if combat_log: OnCMsgDOTACombatLogEntry│
              │  ├── if entities: OnEntity                 │
              │  └── if messages: setupAllCallbacks        │
              └─────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  parser.Start() - SINGLE PASS │
                    │  All callbacks fire during    │
                    │  this one traversal           │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Finalize: resolve strings,   │
                    │  build result structs         │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Return JSON → ParseResult    │
                    └───────────────────────────────┘
```

---

## Seek Implementation

Manta (Go) does not support seeking. Demo files are sequential. To enable seeking:

### Option A: Keyframe Index (Recommended)

```
First pass: Scan file, record positions of full-state packets
┌─────────────────────────────────────────────────────────────┐
│  Keyframe 0: tick=0,     offset=0,       game_time=-90.0   │
│  Keyframe 1: tick=1800,  offset=124532,  game_time=0.0     │
│  Keyframe 2: tick=3600,  offset=248104,  game_time=60.0    │
│  Keyframe 3: tick=5400,  offset=371256,  game_time=120.0   │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘

Seek to tick 5000:
1. Find keyframe with tick <= 5000 (Keyframe 2, tick=3600)
2. Seek file to offset 248104
3. Parse forward from tick 3600 to tick 5000
4. Return state at tick 5000
```

### Option B: Full State Snapshots (Memory-heavy)

Save complete entity state at intervals. Seek = restore snapshot.
Not recommended for large files due to memory usage.

---

## Implementation Phases

### Phase 1: Single-Pass Parsing
**Goal**: Eliminate multi-parse problem

1. Refactor Go: extract collector setup functions from existing `Run*` functions
2. Add `parser.go` with `Parse()` that reuses collectors
3. Add Python `Parser` class with `parse()` method
4. Add tests for new API
5. Verify existing tests still pass

**Result**: `parser.parse(header=True, combat_log=True, entities=True)` works

### Phase 2: Streaming Support
**Goal**: Enable callback and generator patterns

1. Add `stream.go` with handle management
2. Add `Open()`, `Next()`, `Close()` to Go
3. Add `run()` and `stream()` to Python Parser
4. Add callback decorator support

**Result**: `parser.run()` with `@parser.on_combat_log` works

### Phase 3: Seek Support
**Goal**: Enable jumping to specific ticks

1. Add `index.go` with keyframe building
2. Add `BuildIndex()`, `Seek()`, `Snapshot()` to Go
3. Add `build_index()`, `seek()`, `snapshot()` to Python

**Result**: `parser.seek(tick=50000)` works

### Phase 4: Cleanup & Documentation
**Goal**: Remove legacy code, update all docs

1. Migrate all tests to new API
2. Update all documentation
3. Remove old `MantaParser` class
4. Remove old `Parse*` Go functions
5. Consolidate Go files to match manta structure

---

## Documentation Updates Required

### Files to Update

| File | Changes |
|------|---------|
| `docs/index.md` | Update overview, quick start examples |
| `docs/getting-started.md` | Rewrite for new `Parser` API |
| `docs/examples.md` | Rewrite all examples for single-pass |
| `docs/api/manta-parser.md` | **DELETE** - Replace with `docs/api/parser.md` |
| `docs/api/parser.md` | **NEW** - Document `Parser` class |
| `docs/api/models.md` | Update model references |
| `docs/api/index.md` | Update API overview |
| `docs/guides/combat-log.md` | Update for new API |
| `docs/guides/entities.md` | Update for new API |
| `docs/guides/game-events.md` | Update for new API |
| `docs/guides/modifiers.md` | Update for new API |
| `docs/guides/universal.md` | Update for streaming/messages |
| `docs/guides/unit-orders.md` | Update for new API |
| `docs/guides/index.md` | Update guide overview |
| `docs/reference/callbacks.md` | Update callback registration |
| `docs/reference/combat-log.md` | Update types reference |
| `docs/reference/entities.md` | Update types reference |
| `docs/reference/game-events.md` | Update types reference |
| `docs/reference/modifiers.md` | Update types reference |
| `docs/reference/string-tables.md` | Update types reference |
| `docs/reference/index.md` | Update reference overview |
| `README.md` | Update quick start, examples |
| `CLAUDE.md` | Update API quick reference |

### New Documentation Files

| File | Purpose |
|------|---------|
| `docs/guides/streaming.md` | **NEW** - Streaming with callbacks/generators |
| `docs/guides/seeking.md` | **NEW** - Seek and range parsing |
| `docs/api/parser.md` | **NEW** - Parser class reference |
| `docs/design/v2-architecture.md` | This document |

### Documentation Structure After Update

```
docs/
├── index.md                    # Overview, installation
├── getting-started.md          # Quick start with new API
├── examples.md                 # Complete examples
│
├── api/
│   ├── index.md               # API overview
│   ├── parser.md              # NEW: Parser class reference
│   └── models.md              # Pydantic models reference
│
├── guides/
│   ├── index.md               # Guides overview
│   ├── combat-log.md          # Combat log guide
│   ├── entities.md            # Entity tracking guide
│   ├── game-events.md         # Game events guide
│   ├── modifiers.md           # Modifiers guide
│   ├── streaming.md           # NEW: Streaming guide
│   └── seeking.md             # NEW: Seek/range guide
│
├── reference/
│   ├── index.md               # Reference overview
│   ├── callbacks.md           # All 272 callbacks
│   ├── combat-log.md          # Combat log types
│   ├── entities.md            # Entity types
│   ├── game-events.md         # 364 game event types
│   ├── modifiers.md           # Modifier types
│   └── string-tables.md       # String table reference
│
└── design/
    └── v2-architecture.md     # This document
```

---

## Caveats and Considerations

### 1. Callback Conflicts
When multiple collectors register the same callback (e.g., both combat_log and messages want `OnCMsgDOTACombatLogEntry`), we need to handle this gracefully. Solution: Each collector adds to a shared list, callbacks dispatch to all registered handlers.

### 2. Memory Usage
Collecting all data types simultaneously uses more memory than parsing one at a time. For very large replays with all collectors enabled, memory could be significant. Consider adding a `low_memory` mode that streams to disk.

### 3. Streaming vs Batch
The `parse()` method (batch) and `stream()` method (streaming) are mutually exclusive. You can't call both on the same parser instance. This is by design - they're different paradigms.

### 4. Seek Limitations
- Seeking requires an index (built on first pass or explicitly)
- Seeking to an arbitrary tick may require parsing forward from a keyframe
- Entity state at a tick requires parsing up to that tick (can't jump directly)

### 5. Thread Safety
Parser instances are NOT thread-safe. Don't share across threads. Create separate parsers per thread if needed.

### 6. Error Handling
Following project principles: fail fast, no fallbacks. If parsing fails, the error propagates immediately. No partial results, no silent failures.

---

## Migration Path

```python
# v1 (old) - 5 parses
parser = MantaParser()
h = parser.parse_header("demo.dem")
g = parser.parse_game_info("demo.dem")
c = parser.parse_combat_log("demo.dem")
e = parser.parse_entities("demo.dem")
m = parser.parse_universal("demo.dem", "Chat")

# v2 (new) - 1 parse
parser = Parser("demo.dem")
result = parser.parse(
    header=True,
    game_info=True,
    combat_log=True,
    entities=True,
    messages={"filter": "Chat"},
)
# result.header, result.game_info, result.combat_log, etc.
```

---

## Performance Comparison

| Scenario | v1 (current) | v2 (new) | Improvement |
|----------|-------------|----------|-------------|
| Header only | 1 parse | 1 parse | Same |
| Header + game_info | 2 parses | 1 parse | 2× |
| Full analysis (5 types) | 5 parses | 1 parse | 5× |
| Streaming with callbacks | Not possible | 1 parse | ∞ |
| Seek to specific tick | Full parse | Partial parse | Variable |

---

## References

- [dotabuff/manta](https://github.com/dotabuff/manta) - Go library we wrap
- [Clarity](https://github.com/skadistats/clarity) - Java parser with seek support (inspiration for Phase 3)
- [CLAUDE.md](../../CLAUDE.md) - Project principles and guidelines
