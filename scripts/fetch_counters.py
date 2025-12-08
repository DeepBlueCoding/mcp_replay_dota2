#!/usr/bin/env python3
"""
Fetch hero counter picks from OpenDota and generate WHY descriptions using Claude.

Usage:
    # Fetch matchups only (no AI descriptions)
    uv run python scripts/fetch_counters.py --no-ai

    # Full run with AI descriptions (requires ANTHROPIC_API_KEY)
    uv run python scripts/fetch_counters.py

    # Process specific heroes only
    uv run python scripts/fetch_counters.py --heroes 1,2,3

    # Dry run (don't save)
    uv run python scripts/fetch_counters.py --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.hero_counters import CounterMatchup, HeroCounters, HeroCountersDatabase

# Configuration
MIN_GAMES_THRESHOLD = 100
MIN_ADVANTAGE_THRESHOLD = 2.0
TOP_COUNTERS_LIMIT = 8
OPENDOTA_API_BASE = "https://api.opendota.com/api"
RATE_LIMIT_DELAY = 1.2


def load_heroes_constants() -> dict[str, Any]:
    """Load heroes.json from local constants."""
    heroes_path = Path(__file__).parent.parent / "data" / "constants" / "heroes.json"
    with open(heroes_path) as f:
        return json.load(f)


def load_abilities_constants() -> dict[str, Any]:
    """Load abilities.json from local constants."""
    abilities_path = Path(__file__).parent.parent / "data" / "constants" / "abilities.json"
    with open(abilities_path) as f:
        return json.load(f)


def load_hero_abilities_constants() -> dict[str, Any]:
    """Load hero_abilities.json mapping."""
    path = Path(__file__).parent.parent / "data" / "constants" / "hero_abilities.json"
    with open(path) as f:
        return json.load(f)


def get_hero_ability_descriptions(
    hero_name: str,
    hero_abilities: dict[str, Any],
    abilities: dict[str, Any]
) -> list[dict[str, str]]:
    """Get ability names and descriptions for a hero."""
    hero_data = hero_abilities.get(hero_name, {})
    ability_names = hero_data.get("abilities", [])

    result = []
    for ability_name in ability_names:
        if ability_name.startswith("generic_"):
            continue
        ability_data = abilities.get(ability_name, {})
        if ability_data.get("dname"):
            result.append({
                "name": ability_data.get("dname", ability_name),
                "desc": ability_data.get("desc", "")
            })
    return result


async def fetch_hero_matchups(client: httpx.AsyncClient, hero_id: int) -> list[dict]:
    """Fetch matchup data for a hero from OpenDota."""
    url = f"{OPENDOTA_API_BASE}/heroes/{hero_id}/matchups"
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


def calculate_advantage(games: int, wins: int) -> float:
    """Calculate win rate advantage over 50%."""
    if games == 0:
        return 0.0
    win_rate = (wins / games) * 100
    return round(win_rate - 50.0, 2)


async def fetch_all_matchups(
    heroes: dict[str, Any],
    hero_ids: list[int] | None = None
) -> dict[int, list[dict]]:
    """Fetch matchup data for all heroes."""
    all_matchups = {}
    hero_list = hero_ids or [int(h) for h in heroes.keys()]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, hero_id in enumerate(hero_list):
            hero_data = heroes.get(str(hero_id), {})
            hero_name = hero_data.get("localized_name", f"Hero {hero_id}")
            print(f"  [{i+1}/{len(hero_list)}] Fetching matchups for {hero_name}...")

            try:
                matchups = await fetch_hero_matchups(client, hero_id)
                all_matchups[hero_id] = matchups
            except Exception as e:
                print(f"    Error fetching {hero_name}: {e}")
                all_matchups[hero_id] = []

            await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_matchups


def process_matchups(
    hero_id: int,
    matchups: list[dict],
    heroes: dict[str, Any],
    min_games: int = MIN_GAMES_THRESHOLD,
    min_advantage: float = MIN_ADVANTAGE_THRESHOLD,
    top_n: int = TOP_COUNTERS_LIMIT
) -> tuple[list[dict], list[dict]]:
    """
    Process raw matchups into counters and good_against lists.

    Returns (counters, good_against) where:
    - counters: heroes that beat this hero (negative advantage for hero)
    - good_against: heroes this hero beats (positive advantage for hero)
    """
    counters = []
    good_against = []

    for matchup in matchups:
        games = matchup.get("games_played", 0)
        if games < min_games:
            continue

        wins = matchup.get("wins", 0)
        advantage = calculate_advantage(games, wins)

        counter_hero_id = matchup.get("hero_id")
        counter_data = heroes.get(str(counter_hero_id), {})

        entry = {
            "hero_id": counter_hero_id,
            "hero_name": counter_data.get("name", f"npc_dota_hero_{counter_hero_id}"),
            "localized_name": counter_data.get("localized_name", f"Hero {counter_hero_id}"),
            "advantage": advantage,
            "games_sampled": games,
            "reason": ""
        }

        if advantage <= -min_advantage:
            entry["advantage"] = abs(advantage)
            counters.append(entry)
        elif advantage >= min_advantage:
            good_against.append(entry)

    counters.sort(key=lambda x: x["advantage"], reverse=True)
    good_against.sort(key=lambda x: x["advantage"], reverse=True)

    return counters[:top_n], good_against[:top_n]


def build_ai_prompt(
    hero_name: str,
    hero_localized: str,
    hero_abilities: list[dict],
    counter_name: str,
    counter_localized: str,
    counter_abilities: list[dict],
    advantage: float,
    is_counter: bool
) -> str:
    """Build the prompt for Claude to generate WHY description."""
    hero_abilities_text = "\n".join(
        f"  - {a['name']}: {a['desc']}" for a in hero_abilities if a['desc']
    )
    counter_abilities_text = "\n".join(
        f"  - {a['name']}: {a['desc']}" for a in counter_abilities if a['desc']
    )

    if is_counter:
        direction = f"{counter_localized} COUNTERS {hero_localized}"
        context = f"{counter_localized} has a {advantage}% win rate advantage against {hero_localized}."
    else:
        direction = f"{hero_localized} IS GOOD AGAINST {counter_localized}"
        context = f"{hero_localized} has a {advantage}% win rate advantage against {counter_localized}."

    return f"""Explain in 1-2 sentences why {direction} in Dota 2.

{context}

{hero_localized}'s abilities:
{hero_abilities_text}

{counter_localized}'s abilities:
{counter_abilities_text}

Focus on specific ability interactions, mechanics, or playstyle conflicts.
Be concise and specific. No generic statements like "has good burst damage".
Start directly with the reason, don't repeat the hero names at the start."""


async def generate_reason_with_claude(
    client: Any,
    prompt: str
) -> str:
    """Generate a WHY description using Claude."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"    Claude API error: {e}")
        return ""


async def generate_all_reasons(
    database: HeroCountersDatabase,
    heroes: dict[str, Any],
    hero_abilities_map: dict[str, Any],
    abilities: dict[str, Any]
) -> None:
    """Generate WHY descriptions for all matchups using Claude."""
    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        print("Skipping AI reason generation. Set ANTHROPIC_API_KEY environment variable.")
        return

    total_matchups = sum(
        len(h.counters) + len(h.good_against)
        for h in database.heroes.values()
    )
    processed = 0

    for hero_id, hero_data in database.heroes.items():
        hero_name = hero_data.hero_name
        hero_localized = hero_data.localized_name
        hero_abilities_list = get_hero_ability_descriptions(
            hero_name, hero_abilities_map, abilities
        )

        for matchup in hero_data.counters:
            processed += 1
            if matchup.reason:
                continue

            counter_abilities_list = get_hero_ability_descriptions(
                matchup.hero_name, hero_abilities_map, abilities
            )

            prompt = build_ai_prompt(
                hero_name, hero_localized, hero_abilities_list,
                matchup.hero_name, matchup.localized_name, counter_abilities_list,
                matchup.advantage, is_counter=True
            )

            print(f"  [{processed}/{total_matchups}] {matchup.localized_name} counters {hero_localized}...")
            reason = await generate_reason_with_claude(client, prompt)
            matchup.reason = reason
            await asyncio.sleep(0.5)

        for matchup in hero_data.good_against:
            processed += 1
            if matchup.reason:
                continue

            counter_abilities_list = get_hero_ability_descriptions(
                matchup.hero_name, hero_abilities_map, abilities
            )

            prompt = build_ai_prompt(
                hero_name, hero_localized, hero_abilities_list,
                matchup.hero_name, matchup.localized_name, counter_abilities_list,
                matchup.advantage, is_counter=False
            )

            print(f"  [{processed}/{total_matchups}] {hero_localized} good vs {matchup.localized_name}...")
            reason = await generate_reason_with_claude(client, prompt)
            matchup.reason = reason
            await asyncio.sleep(0.5)


async def main():
    parser = argparse.ArgumentParser(description="Fetch hero counter picks from OpenDota")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI reason generation")
    parser.add_argument("--heroes", type=str, help="Comma-separated hero IDs to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't save output file")
    parser.add_argument("--min-games", type=int, default=MIN_GAMES_THRESHOLD,
                        help=f"Minimum games for matchup (default: {MIN_GAMES_THRESHOLD})")
    parser.add_argument("--min-advantage", type=float, default=MIN_ADVANTAGE_THRESHOLD,
                        help=f"Minimum advantage %% (default: {MIN_ADVANTAGE_THRESHOLD})")
    args = parser.parse_args()

    print("Loading hero constants...")
    heroes = load_heroes_constants()
    abilities = load_abilities_constants()
    hero_abilities_map = load_hero_abilities_constants()

    hero_ids = None
    if args.heroes:
        hero_ids = [int(h.strip()) for h in args.heroes.split(",")]
        print(f"Processing {len(hero_ids)} specific heroes")
    else:
        print(f"Processing all {len(heroes)} heroes")

    print("\nFetching matchups from OpenDota API...")
    start_time = time.time()
    all_matchups = await fetch_all_matchups(heroes, hero_ids)
    fetch_time = time.time() - start_time
    print(f"Fetched matchups in {fetch_time:.1f}s")

    print("\nProcessing matchups...")
    database = HeroCountersDatabase(
        version=datetime.now().strftime("%Y-%m-%d"),
        source="opendota",
        min_games_threshold=args.min_games,
        min_advantage_threshold=args.min_advantage,
        heroes={}
    )

    for hero_id, matchups in all_matchups.items():
        hero_data = heroes.get(str(hero_id), {})
        counters, good_against = process_matchups(
            hero_id, matchups, heroes,
            min_games=args.min_games,
            min_advantage=args.min_advantage
        )

        hero_counters = HeroCounters(
            hero_id=hero_id,
            hero_name=hero_data.get("name", f"npc_dota_hero_{hero_id}"),
            localized_name=hero_data.get("localized_name", f"Hero {hero_id}"),
            counters=[CounterMatchup(**c) for c in counters],
            good_against=[CounterMatchup(**g) for g in good_against]
        )
        database.heroes[str(hero_id)] = hero_counters

    total_counters = sum(len(h.counters) for h in database.heroes.values())
    total_good = sum(len(h.good_against) for h in database.heroes.values())
    print(f"Found {total_counters} counter matchups and {total_good} favorable matchups")

    if not args.no_ai:
        print("\nGenerating AI descriptions...")
        await generate_all_reasons(database, heroes, hero_abilities_map, abilities)

    if not args.dry_run:
        output_path = Path(__file__).parent.parent / "data" / "constants" / "hero_counters.json"
        print(f"\nSaving to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(database.model_dump(), f, indent=2)
        print("Done!")
    else:
        print("\nDry run - not saving output")
        print(json.dumps(database.model_dump(), indent=2)[:2000] + "...")


if __name__ == "__main__":
    asyncio.run(main())
