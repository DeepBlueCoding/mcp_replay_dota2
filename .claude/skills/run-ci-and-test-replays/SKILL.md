---
name: run-ci-and-test-replays
description: >-
  Runs the local CI gate (ruff + mypy + pytest) and writes/maintains real-values golden-master
  tests against the session-scoped replay fixtures for mcp-replay-dota2. Use whenever the user
  wants to run the tests, run CI locally, write or fix a test, add a fixture, test against real
  match data, run ruff/mypy/pytest, or check things "before pushing" in this Dota 2 MCP server.
  Encodes the exact commands, the uv-sync (not uv-pip) gotcha, the fixtures-only rule, the
  golden-master verified constants, the stable-ID-vs-display-name lesson, the pytest markers,
  and why CI runs only the smaller replay.
---

# Run CI and write replay tests for mcp-replay-dota2

`CLAUDE.md` (repo root) states the policy; this skill is the operational detail.

## The CI gate (all three mandatory before any commit/push, in this order)

```bash
uv run ruff check src/ tests/ dota_match_mcp_server.py
uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports
uv run pytest
```

For one new test, run just it first:
```bash
uv run pytest tests/services/farming/test_farming_service.py::TestMultiCampDetection -v
```

Install deps with `uv sync` (or `uv sync --group dev`), NOT `uv pip install`. Always prefix with
`uv run`. Never call `python`/`pip` directly.

## Replay files & cache

Tests need two real replays in `~/dota2/replays/` (override the dir with `DOTA_REPLAY_CACHE`):
- `8461956309.dem` — primary, ~400 MB.
- `8594217096.dem` — secondary (OG match), smaller.

`conftest.py` parses each replay ONCE at session start (session-scoped, in-memory + diskcache)
and injects ~65 pre-sliced fixtures (e.g. `hero_deaths`, `combat_log_280_290`,
`combat_log_280_290_earthshaker`, `objectives`, `rune_pickups`, and the `*_2` variants for
match 2). `asyncio_mode=auto`, so async test functions need no decorator. Disk cache lives at
`~/.cache/mcp_dota2/parsed_replays_v2` with a 7-day TTL.

NEVER call `Parser` or `get_parsed_data` directly in a test — request fixtures instead. If your
test needs data no fixture provides, add a new session-scoped fixture in `conftest.py` that
derives from the already-parsed data (don't parse again).

## Golden-master verified constants (assert these EXACT values)

Match `8461956309`: first blood = `earthshaker` killed by `disruptor` at `288.0s` ("4:48").

Match `8594217096`: first blood = `batrider` by `pugna` at `84.0s` ("1:24"); total deaths after
start = `53`; roshan kills = `3`; tower kills = `14`; barracks kills = `6`; rune pickups = `13`;
courier kills = `5`.

Good test asserts a real victim/killer/time/count. Bad test asserts `isinstance(...)`, `len > 0`,
or key existence — those are banned (see `CLAUDE.md`).

## Stable-ID lesson (commit 17473c4) — for live OpenDota data

OpenDota display names are MUTABLE (Yatoro -> yatoro, BetBoom -> BB). Golden-mastering them is
banned. For pro players/teams assert the STABLE id (`account_id` / `team_id`) and match names
case-insensitively. Also avoid valueless range checks (e.g. "duration between X and Y") — assert
a real expected value or a stable id.

## pytest markers (`pyproject.toml`)

`fast` (no replay parsing), `slow` (parses replays, 1+ min), `integration` (external/network),
`core` (essential), `use_case` (documented use cases). Deselect the heavy ones with
`uv run pytest -m "not slow"`. `--strict-markers` is on, so unknown markers error.

## Why CI differs from local

`.github/workflows/test.yml` deliberately runs ONLY
`tests/examples/test_match_8594217096.py -v` (the smaller replay) because the ~400 MB replay OOMs
GitHub runners. The full suite runs locally only. The workflow has `concurrency
cancel-in-progress: false` so a release push won't cancel an in-flight test run.

## HARD CONSTRAINT for this machine right now

A full python-manta test run may be in progress. Do NOT kick off `uv run pytest` or anything that
re-parses replays unless the user explicitly asks. Verify statically (read files, grep) when you
can.
