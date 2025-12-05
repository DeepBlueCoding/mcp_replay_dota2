"""
Map data resource for Dota 2.

Provides static map information including tower positions, neutral camps,
rune spawns, and other landmarks.
"""

from src.models.map_data import (
    Ancient,
    Barracks,
    Landmark,
    MapCoordinate,
    MapData,
    MapLane,
    NeutralCamp,
    Outpost,
    RuneRules,
    RuneSpawn,
    RuneTypeInfo,
    Shop,
    Tower,
)


def get_map_data() -> MapData:
    """
    Get complete Dota 2 map data.

    Positions are in world coordinates extracted from replay data.
    The map spans roughly -8000 to +8000 in both X and Y axes.
    Origin (0,0) is approximately center of map.
    Radiant base is bottom-left (negative X, negative Y).
    Dire base is top-right (positive X, positive Y).
    """

    # Tower positions (extracted from replay entity data)
    towers = [
        # Radiant Tier 1
        Tower(name="radiant_t1_top", team="radiant", tier=1, lane="top",
              position=MapCoordinate(x=-6336, y=1856)),
        Tower(name="radiant_t1_mid", team="radiant", tier=1, lane="mid",
              position=MapCoordinate(x=-1544, y=-1408)),
        Tower(name="radiant_t1_bot", team="radiant", tier=1, lane="bot",
              position=MapCoordinate(x=4904, y=-6198)),

        # Radiant Tier 2
        Tower(name="radiant_t2_top", team="radiant", tier=2, lane="top",
              position=MapCoordinate(x=-6464, y=-872)),
        Tower(name="radiant_t2_mid", team="radiant", tier=2, lane="mid",
              position=MapCoordinate(x=-3190, y=-2926)),
        Tower(name="radiant_t2_bot", team="radiant", tier=2, lane="bot",
              position=MapCoordinate(x=-360, y=-6256)),

        # Radiant Tier 3
        Tower(name="radiant_t3_top", team="radiant", tier=3, lane="top",
              position=MapCoordinate(x=-6592, y=-3408)),
        Tower(name="radiant_t3_mid", team="radiant", tier=3, lane="mid",
              position=MapCoordinate(x=-4640, y=-4144)),
        Tower(name="radiant_t3_bot", team="radiant", tier=3, lane="bot",
              position=MapCoordinate(x=-3952, y=-6112)),

        # Radiant Tier 4 (Ancient towers)
        Tower(name="radiant_t4_top", team="radiant", tier=4, lane="base",
              position=MapCoordinate(x=-5392, y=-5192)),
        Tower(name="radiant_t4_bot", team="radiant", tier=4, lane="base",
              position=MapCoordinate(x=-5712, y=-4864)),

        # Dire Tier 1
        Tower(name="dire_t1_top", team="dire", tier=1, lane="top",
              position=MapCoordinate(x=-5275, y=5928)),
        Tower(name="dire_t1_mid", team="dire", tier=1, lane="mid",
              position=MapCoordinate(x=524, y=652)),
        Tower(name="dire_t1_bot", team="dire", tier=1, lane="bot",
              position=MapCoordinate(x=6269, y=-2240)),

        # Dire Tier 2
        Tower(name="dire_t2_top", team="dire", tier=2, lane="top",
              position=MapCoordinate(x=-128, y=6016)),
        Tower(name="dire_t2_mid", team="dire", tier=2, lane="mid",
              position=MapCoordinate(x=2496, y=2112)),
        Tower(name="dire_t2_bot", team="dire", tier=2, lane="bot",
              position=MapCoordinate(x=6400, y=384)),

        # Dire Tier 3
        Tower(name="dire_t3_top", team="dire", tier=3, lane="top",
              position=MapCoordinate(x=3552, y=5776)),
        Tower(name="dire_t3_mid", team="dire", tier=3, lane="mid",
              position=MapCoordinate(x=4272, y=3759)),
        Tower(name="dire_t3_bot", team="dire", tier=3, lane="bot",
              position=MapCoordinate(x=6336, y=3032)),

        # Dire Tier 4 (Ancient towers)
        Tower(name="dire_t4_top", team="dire", tier=4, lane="base",
              position=MapCoordinate(x=5280, y=4432)),
        Tower(name="dire_t4_bot", team="dire", tier=4, lane="base",
              position=MapCoordinate(x=4944, y=4776)),
    ]

    # Barracks positions
    barracks = [
        # Radiant
        Barracks(name="radiant_melee_top", team="radiant", lane="top", type="melee",
                 position=MapCoordinate(x=-6400, y=-3600)),
        Barracks(name="radiant_ranged_top", team="radiant", lane="top", type="ranged",
                 position=MapCoordinate(x=-6200, y=-3800)),
        Barracks(name="radiant_melee_mid", team="radiant", lane="mid", type="melee",
                 position=MapCoordinate(x=-4800, y=-4400)),
        Barracks(name="radiant_ranged_mid", team="radiant", lane="mid", type="ranged",
                 position=MapCoordinate(x=-4600, y=-4600)),
        Barracks(name="radiant_melee_bot", team="radiant", lane="bot", type="melee",
                 position=MapCoordinate(x=-4200, y=-6300)),
        Barracks(name="radiant_ranged_bot", team="radiant", lane="bot", type="ranged",
                 position=MapCoordinate(x=-4000, y=-6500)),

        # Dire
        Barracks(name="dire_melee_top", team="dire", lane="top", type="melee",
                 position=MapCoordinate(x=3800, y=6000)),
        Barracks(name="dire_ranged_top", team="dire", lane="top", type="ranged",
                 position=MapCoordinate(x=4000, y=6200)),
        Barracks(name="dire_melee_mid", team="dire", lane="mid", type="melee",
                 position=MapCoordinate(x=4500, y=4000)),
        Barracks(name="dire_ranged_mid", team="dire", lane="mid", type="ranged",
                 position=MapCoordinate(x=4700, y=4200)),
        Barracks(name="dire_melee_bot", team="dire", lane="bot", type="melee",
                 position=MapCoordinate(x=6500, y=3300)),
        Barracks(name="dire_ranged_bot", team="dire", lane="bot", type="ranged",
                 position=MapCoordinate(x=6700, y=3500)),
    ]

    # Ancients
    ancients = [
        Ancient(team="radiant", position=MapCoordinate(x=-5600, y=-5000)),
        Ancient(team="dire", position=MapCoordinate(x=5100, y=4600)),
    ]

    # Neutral camps
    neutral_camps = [
        # Radiant jungle
        NeutralCamp(name="radiant_small_camp_1", side="radiant", tier="small",
                    position=MapCoordinate(x=-3200, y=-4700)),
        NeutralCamp(name="radiant_small_camp_2", side="radiant", tier="small",
                    position=MapCoordinate(x=-2400, y=-3900)),
        NeutralCamp(name="radiant_medium_camp_1", side="radiant", tier="medium",
                    position=MapCoordinate(x=-4300, y=-3400)),
        NeutralCamp(name="radiant_medium_camp_2", side="radiant", tier="medium",
                    position=MapCoordinate(x=-1100, y=-4200)),
        NeutralCamp(name="radiant_large_camp_1", side="radiant", tier="large",
                    position=MapCoordinate(x=-3600, y=-700)),
        NeutralCamp(name="radiant_large_camp_2", side="radiant", tier="large",
                    position=MapCoordinate(x=-600, y=-3200)),
        NeutralCamp(name="radiant_ancient_camp", side="radiant", tier="ancient",
                    position=MapCoordinate(x=-2900, y=-200)),

        # Dire jungle
        NeutralCamp(name="dire_small_camp_1", side="dire", tier="small",
                    position=MapCoordinate(x=3700, y=700)),
        NeutralCamp(name="dire_small_camp_2", side="dire", tier="small",
                    position=MapCoordinate(x=2000, y=4100)),
        NeutralCamp(name="dire_medium_camp_1", side="dire", tier="medium",
                    position=MapCoordinate(x=4300, y=2200)),
        NeutralCamp(name="dire_medium_camp_2", side="dire", tier="medium",
                    position=MapCoordinate(x=900, y=4400)),
        NeutralCamp(name="dire_large_camp_1", side="dire", tier="large",
                    position=MapCoordinate(x=3700, y=4800)),
        NeutralCamp(name="dire_large_camp_2", side="dire", tier="large",
                    position=MapCoordinate(x=1200, y=2600)),
        NeutralCamp(name="dire_ancient_camp", side="dire", tier="ancient",
                    position=MapCoordinate(x=3200, y=-500)),

        # Triangle camps
        NeutralCamp(name="radiant_triangle_large", side="radiant", tier="large",
                    position=MapCoordinate(x=3400, y=-4600)),
        NeutralCamp(name="radiant_triangle_medium", side="radiant", tier="medium",
                    position=MapCoordinate(x=4600, y=-3400)),
        NeutralCamp(name="radiant_triangle_ancient", side="radiant", tier="ancient",
                    position=MapCoordinate(x=2000, y=-6000)),
        NeutralCamp(name="dire_triangle_large", side="dire", tier="large",
                    position=MapCoordinate(x=-3700, y=4200)),
        NeutralCamp(name="dire_triangle_medium", side="dire", tier="medium",
                    position=MapCoordinate(x=-4800, y=3200)),
        NeutralCamp(name="dire_triangle_ancient", side="dire", tier="ancient",
                    position=MapCoordinate(x=-2200, y=5800)),
    ]

    # Rune spawns
    rune_spawns = [
        # Power runes (river)
        RuneSpawn(name="power_rune_top", type="power",
                  position=MapCoordinate(x=-1900, y=1200)),
        RuneSpawn(name="power_rune_bot", type="power",
                  position=MapCoordinate(x=2400, y=-1800)),

        # Bounty runes
        RuneSpawn(name="bounty_radiant_jungle", type="bounty",
                  position=MapCoordinate(x=-4300, y=-1800)),
        RuneSpawn(name="bounty_radiant_triangle", type="bounty",
                  position=MapCoordinate(x=4100, y=-4100)),
        RuneSpawn(name="bounty_dire_jungle", type="bounty",
                  position=MapCoordinate(x=4100, y=1400)),
        RuneSpawn(name="bounty_dire_triangle", type="bounty",
                  position=MapCoordinate(x=-4300, y=3900)),

        # Wisdom runes
        RuneSpawn(name="wisdom_radiant", type="wisdom",
                  position=MapCoordinate(x=-6200, y=1000)),
        RuneSpawn(name="wisdom_dire", type="wisdom",
                  position=MapCoordinate(x=5800, y=-1400)),

        # Water runes (river)
        RuneSpawn(name="water_rune_1", type="water",
                  position=MapCoordinate(x=-600, y=-200)),
        RuneSpawn(name="water_rune_2", type="water",
                  position=MapCoordinate(x=600, y=200)),
    ]

    # Rune spawn rules and timing
    rune_rules = RuneRules(
        power_runes=RuneTypeInfo(
            name="power",
            first_spawn=360,  # 6:00
            interval=120,  # every 2 minutes
            effect="Random buff: haste, double damage, arcane, invis, regen, or shield",
            duration=45,
        ),
        bounty_runes=RuneTypeInfo(
            name="bounty",
            first_spawn=0,  # 0:00
            interval=180,  # every 3 minutes
            effect="Grants gold to the hero and all allied heroes",
            duration=None,
        ),
        wisdom_runes=RuneTypeInfo(
            name="wisdom",
            first_spawn=420,  # 7:00
            interval=420,  # every 7 minutes
            effect="Grants experience based on game time",
            duration=None,
        ),
        water_runes=RuneTypeInfo(
            name="water",
            first_spawn=120,  # 2:00
            interval=120,  # every 2 minutes, but stops after 4:00
            effect="Restores health and mana. Only spawns at 2:00 and 4:00",
            duration=None,
        ),
        power_rune_types=[
            "Haste",
            "Double Damage",
            "Arcane",
            "Invisibility",
            "Regeneration",
            "Shield",
            "Illusion",
            "Water",
        ],
    )

    # Outposts
    outposts = [
        Outpost(name="radiant_outpost", side="radiant",
                position=MapCoordinate(x=-3000, y=300)),
        Outpost(name="dire_outpost", side="dire",
                position=MapCoordinate(x=3200, y=200)),
    ]

    # Shops
    shops = [
        Shop(name="radiant_base_shop", type="base", team="radiant",
             position=MapCoordinate(x=-4800, y=-6000)),
        Shop(name="dire_base_shop", type="base", team="dire",
             position=MapCoordinate(x=4400, y=5400)),
        Shop(name="radiant_secret_shop", type="secret", team="radiant",
             position=MapCoordinate(x=-4800, y=-200)),
        Shop(name="dire_secret_shop", type="secret", team="dire",
             position=MapCoordinate(x=4300, y=1000)),
        Shop(name="radiant_side_shop", type="side", team="radiant",
             position=MapCoordinate(x=-6000, y=2500)),
        Shop(name="dire_side_shop", type="side", team="dire",
             position=MapCoordinate(x=5800, y=-2800)),
    ]

    # Notable landmarks
    landmarks = [
        Landmark(name="roshan_pit", description="Roshan's lair - drops Aegis",
                 position=MapCoordinate(x=-2000, y=1100)),
        Landmark(name="radiant_fountain", description="Radiant healing fountain",
                 position=MapCoordinate(x=-6800, y=-6600)),
        Landmark(name="dire_fountain", description="Dire healing fountain",
                 position=MapCoordinate(x=6800, y=6200)),
        Landmark(name="mid_river", description="Center of the river",
                 position=MapCoordinate(x=0, y=-200)),
        Landmark(name="radiant_shrine", description="Radiant jungle shrine area",
                 position=MapCoordinate(x=-2800, y=-2400)),
        Landmark(name="dire_shrine", description="Dire jungle shrine area",
                 position=MapCoordinate(x=2600, y=2000)),
        Landmark(name="tormentor_radiant", description="Radiant Tormentor spawn",
                 position=MapCoordinate(x=-4100, y=-400)),
        Landmark(name="tormentor_dire", description="Dire Tormentor spawn",
                 position=MapCoordinate(x=4100, y=0)),
        Landmark(name="radiant_highground_mid", description="Radiant mid high ground",
                 position=MapCoordinate(x=-3800, y=-3800)),
        Landmark(name="dire_highground_mid", description="Dire mid high ground",
                 position=MapCoordinate(x=3400, y=3200)),
        Landmark(name="radiant_safe_t1_jungle", description="Jungle behind Radiant safe T1",
                 position=MapCoordinate(x=3000, y=-5500)),
        Landmark(name="dire_safe_t1_jungle", description="Jungle behind Dire safe T1",
                 position=MapCoordinate(x=-3500, y=5000)),
    ]

    # Lane definitions
    lanes = [
        MapLane(name="top", radiant_name="offlane", dire_name="safelane"),
        MapLane(name="mid", radiant_name="mid", dire_name="mid"),
        MapLane(name="bot", radiant_name="safelane", dire_name="offlane"),
    ]

    return MapData(
        map_bounds={
            "min_x": -8000,
            "max_x": 8000,
            "min_y": -8000,
            "max_y": 8000,
            "playable_min_x": -7200,
            "playable_max_x": 7200,
            "playable_min_y": -7000,
            "playable_max_y": 6800,
        },
        towers=towers,
        barracks=barracks,
        ancients=ancients,
        neutral_camps=neutral_camps,
        rune_spawns=rune_spawns,
        rune_rules=rune_rules,
        outposts=outposts,
        shops=shops,
        landmarks=landmarks,
        lanes=lanes,
    )


# Singleton
_map_data = None


def get_cached_map_data() -> MapData:
    """Get cached map data."""
    global _map_data
    if _map_data is None:
        _map_data = get_map_data()
    return _map_data
