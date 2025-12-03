"""
Position classification for Dota 2 map coordinates.

Provides functions to classify world coordinates into human-readable
map locations (lanes, regions, nearby landmarks).
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple


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


TOWER_POSITIONS = {
    'radiant_t1_top': (-6336, 1856),
    'radiant_t1_mid': (-360, -6256),
    'radiant_t1_bot': (4904, -6198),
    'radiant_t2_top': (-6464, -872),
    'radiant_t2_mid': (-4640, -4144),
    'radiant_t2_bot': (-3190, -2926),
    'radiant_t3_top': (-6592, -3408),
    'radiant_t3_mid': (-4096, -448),
    'radiant_t3_bot': (-3952, -6112),
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
    closest_tower = None
    min_tower_dist = float('inf')
    for name, pos in TOWER_POSITIONS.items():
        d = _distance((x, y), pos)
        if d < min_tower_dist:
            min_tower_dist = d
            closest_tower = name

    on_dire_side = y > x * 0.8 - 500

    if y > 3500 or (x < -3500 and y > 1500):
        lane = 'top'
    elif y < -3500 or (x > 3500 and y < -1500):
        lane = 'bot'
    elif -2500 < x < 2500 and -2500 < y < 2500:
        lane = 'mid'
    else:
        lane = None

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
