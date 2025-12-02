# Data Models

Pydantic models used for tool responses.

## HeroDeathsResponse

Response from `get_hero_deaths` tool.

```python
class HeroDeathsResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    total_deaths: int = 0
    deaths: List[HeroDeathEvent] = []
```

### HeroDeathEvent

```python
class HeroDeathEvent(BaseModel):
    game_time: float
    game_time_str: str
    killer: str
    victim: str
    killer_is_hero: bool
    ability: Optional[str] = None
```

---

## CombatLogResponse

Response from `get_combat_log` tool.

```python
class CombatLogResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    total_events: int = 0
    filters: Optional[CombatLogFilters] = None
    events: List[CombatLogEvent] = []
```

### CombatLogEvent

```python
class CombatLogEvent(BaseModel):
    type: str
    game_time: float
    game_time_str: str
    attacker: str
    attacker_is_hero: bool
    target: str
    target_is_hero: bool
    ability: Optional[str] = None
    value: Optional[int] = None
```

---

## FightCombatLogResponse

Response from `get_fight_combat_log` tool.

```python
class FightCombatLogResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    hero: Optional[str] = None
    fight_start: float = 0
    fight_start_str: str = ""
    fight_end: float = 0
    fight_end_str: str = ""
    duration: float = 0
    participants: List[str] = []
    total_events: int = 0
    events: List[CombatLogEvent] = []
```

---

## ItemPurchasesResponse

Response from `get_item_purchases` tool.

```python
class ItemPurchasesResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    hero_filter: Optional[str] = None
    total_purchases: int = 0
    purchases: List[ItemPurchaseEvent] = []
```

### ItemPurchaseEvent

```python
class ItemPurchaseEvent(BaseModel):
    game_time: float
    game_time_str: str
    hero: str
    item: str
```

---

## CourierKillsResponse

Response from `get_courier_kills` tool.

```python
class CourierKillsResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    total_kills: int = 0
    kills: List[CourierKillEvent] = []
```

### CourierKillEvent

```python
class CourierKillEvent(BaseModel):
    game_time: float
    game_time_str: str
    killer: str
    killer_is_hero: bool
    team: str
```

---

## ObjectiveKillsResponse

Response from `get_objective_kills` tool.

```python
class ObjectiveKillsResponse(BaseModel):
    success: bool
    match_id: int
    error: Optional[str] = None
    roshan_kills: List[RoshanKillEvent] = []
    tormentor_kills: List[TormentorKillEvent] = []
    tower_kills: List[TowerKillEvent] = []
    barracks_kills: List[BarracksKillEvent] = []
```

### RoshanKillEvent

```python
class RoshanKillEvent(BaseModel):
    game_time: float
    game_time_str: str
    killer: str
    team: str
    kill_number: int
```

### TowerKillEvent

```python
class TowerKillEvent(BaseModel):
    game_time: float
    game_time_str: str
    tower_name: str
    team: str
    tier: int
    lane: str
    killer: str
```
