"""
Position tracking for Dota 2 replays.

Provides methods to get hero positions at specific ticks and classify
map locations into human-readable descriptions.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from python_manta import MantaParser


@dataclass
class MapPosition:
    """A position on the Dota 2 map with classification."""

    x: float
    y: float
    region: str
    lane: Optional[str]
    location: str
    closest_tower: Optional[str]
    tower_distance: int


# Tower positions (extracted from replay data)
TOWER_POSITIONS = {
    # Radiant (team 2) towers
    'radiant_t1_top': (-6336, 1856),
    'radiant_t1_mid': (-360, -6256),
    'radiant_t1_bot': (4904, -6198),
    'radiant_t2_top': (-6464, -872),
    'radiant_t2_mid': (-4640, -4144),
    'radiant_t2_bot': (-3190, -2926),
    'radiant_t3_top': (-6592, -3408),
    'radiant_t3_mid': (-4096, -448),
    'radiant_t3_bot': (-3952, -6112),

    # Dire (team 3) towers
    'dire_t1_top': (-5275, 5928),
    'dire_t1_mid': (524, 652),
    'dire_t1_bot': (6269, -2240),
    'dire_t2_top': (-128, 6016),
    'dire_t2_mid': (2496, 2112),
    'dire_t2_bot': (6400, 384),
    'dire_t3_top': (3552, 5776),
    'dire_t3_mid': (3392, -448),
    'dire_t3_bot': (6336, 3032),
}

# Key map landmarks
LANDMARKS = {
    'roshan_pit': (-2000, 1100),
    'radiant_secret_shop': (-4800, -200),
    'dire_secret_shop': (4300, 1000),
    'radiant_ancient': (-6200, -5800),
    'dire_ancient': (6200, 5200),
    'radiant_outpost': (-3000, 300),
    'dire_outpost': (3200, 200),
}


def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def classify_map_position(x: float, y: float) -> MapPosition:
    """
    Classify a map position into a human-readable location.

    Args:
        x: World X coordinate
        y: World Y coordinate

    Returns:
        MapPosition with region, lane, and nearby landmark info
    """
    # Find closest tower
    closest_tower = None
    min_tower_dist = float('inf')
    for name, pos in TOWER_POSITIONS.items():
        d = _distance((x, y), pos)
        if d < min_tower_dist:
            min_tower_dist = d
            closest_tower = name

    # Determine which side of the river
    # River roughly follows y = 0.8x - 500
    on_dire_side = y > x * 0.8 - 500

    # Determine lane
    if y > 3500 or (x < -3500 and y > 1500):
        lane = 'top'
    elif y < -3500 or (x > 3500 and y < -1500):
        lane = 'bot'
    elif -2500 < x < 2500 and -2500 < y < 2500:
        lane = 'mid'
    else:
        lane = None

    # Determine region
    if x < -5000 and y < -4500:
        region = 'radiant_base'
    elif x > 5000 and y > 4000:
        region = 'dire_base'
    elif lane == 'mid' or (-2000 < x < 2000 and -2000 < y < 2000):
        region = 'river' if -1500 < y - x * 0.8 < 1500 else 'mid_lane'
    elif lane == 'top':
        if on_dire_side:
            region = 'dire_safelane'
        else:
            region = 'radiant_offlane'
    elif lane == 'bot':
        if on_dire_side:
            region = 'dire_offlane'
        else:
            region = 'radiant_safelane'
    elif on_dire_side:
        region = 'dire_jungle'
    else:
        region = 'radiant_jungle'

    # Build human-readable location string
    if min_tower_dist < 1200:
        parts = closest_tower.split('_')
        team = parts[0].capitalize()
        tier = parts[1].upper()
        lane_name = parts[2]
        location = f"{region.replace('_', ' ')}, near {team} {tier} {lane_name}"
    elif region == 'river':
        location = 'river'
    elif region in ('radiant_base', 'dire_base'):
        location = region.replace('_', ' ')
    else:
        location = region.replace('_', ' ')

    return MapPosition(
        x=x,
        y=y,
        region=region,
        lane=lane,
        location=location,
        closest_tower=closest_tower if min_tower_dist < 1200 else None,
        tower_distance=int(min_tower_dist)
    )


class PositionTracker:
    """Tracks hero positions during replay parsing."""

    def __init__(self):
        self._parser = MantaParser()
        self._hero_positions_cache: Dict[int, Dict[str, Tuple[float, float]]] = {}

    def get_hero_position_at_tick(
        self,
        replay_path: Path,
        hero_name: str,
        tick: int,
    ) -> Optional[MapPosition]:
        """
        Get a hero's position at a specific tick.

        Args:
            replay_path: Path to the replay file
            hero_name: Hero name (lowercase, e.g., 'earthshaker')
            tick: Game tick to query

        Returns:
            MapPosition or None if not found
        """
        # Query all heroes at the tick (slightly before to ensure alive state)
        entities = self._parser.query_entities(
            str(replay_path),
            class_filter='Hero',
            at_tick=tick - 30,
            max_entities=20
        )

        hero_lower = hero_name.lower()

        for entity in entities.entities:
            class_name = entity.class_name.replace('CDOTA_Unit_Hero_', '').lower()
            if class_name != hero_lower:
                continue

            props = entity.properties
            cell_x = props.get('CBodyComponent.m_cellX', 0)
            cell_y = props.get('CBodyComponent.m_cellY', 0)
            vec_x = props.get('CBodyComponent.m_vecX', 0)
            vec_y = props.get('CBodyComponent.m_vecY', 0)
            health = props.get('m_iHealth', 0)

            # Calculate world position
            world_x = (cell_x - 128) * 128 + vec_x
            world_y = (cell_y - 128) * 128 + vec_y

            # Skip invalid positions (off-map or dead)
            if world_x < -10000 or health <= 0:
                continue

            return classify_map_position(world_x, world_y)

        return None

    def get_all_hero_positions_at_tick(
        self,
        replay_path: Path,
        tick: int,
    ) -> Dict[str, MapPosition]:
        """
        Get all hero positions at a specific tick.

        Args:
            replay_path: Path to the replay file
            tick: Game tick to query

        Returns:
            Dict mapping hero name to MapPosition
        """
        entities = self._parser.query_entities(
            str(replay_path),
            class_filter='Hero',
            at_tick=tick,
            max_entities=20
        )

        positions = {}

        for entity in entities.entities:
            class_name = entity.class_name.replace('CDOTA_Unit_Hero_', '').lower()

            props = entity.properties
            cell_x = props.get('CBodyComponent.m_cellX', 0)
            cell_y = props.get('CBodyComponent.m_cellY', 0)
            vec_x = props.get('CBodyComponent.m_vecX', 0)
            vec_y = props.get('CBodyComponent.m_vecY', 0)
            props.get('m_iHealth', 0)

            world_x = (cell_x - 128) * 128 + vec_x
            world_y = (cell_y - 128) * 128 + vec_y

            # Skip invalid positions
            if world_x < -10000:
                continue

            # Skip if already have this hero (avoid duplicates from illusions etc)
            if class_name in positions:
                continue

            positions[class_name] = classify_map_position(world_x, world_y)

        return positions


# Singleton instance
position_tracker = PositionTracker()
