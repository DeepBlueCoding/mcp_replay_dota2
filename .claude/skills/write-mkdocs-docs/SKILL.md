---
name: write-mkdocs-docs
description: >-
  Writes and updates the mkdocs-material documentation for mcp-replay-dota2: places tool docs on
  the correct API category page, registers new pages in the mkdocs.yml nav, follows the
  AI-Summary admonition style, and keeps the TWO separate changelogs straight. Use whenever the
  user wants to update the docs, document a tool/feature/integration, add a nav entry, write an
  mkdocs page, edit docs/api, or add a changelog entry for this Dota 2 MCP server. Encodes the
  mandatory docs-per-change discipline and the docs/changelog.md vs CHANGELOG.md distinction.
---

# Write mkdocs docs for mcp-replay-dota2

`CLAUDE.md` (repo root) makes this MANDATORY: every feature/bugfix must (1) add a real-values
test, (2) update `docs/api/tools/`, (3) add an entry to `docs/changelog.md`. This skill is the
docs half.

Site stack: mkdocs-material + `mike` for versioning, deployed to gh-pages. Install docs deps via
the `docs` dependency-group (mkdocs-material, mike, mkdocstrings[python]).

## Where a tool doc goes (by category, NOT by source module)

| Page | Covers |
|---|---|
| `docs/api/tools/match-analysis.md` | download/delete_replay, hero_deaths, hero_performance, combat log, item purchases, objective kills, match_timeline/info/heroes/players, runes, courier, draft |
| `docs/api/tools/game-state.md` | list_fights, get_teamfights, get_fight, camp_stacks, jungle_summary, snapshot_at_time, hero_positions, position_timeline, fight_replay |
| `docs/api/tools/farming-rotation.md` | get_farming_pattern, get_rotation_analysis |
| `docs/api/tools/lane-analysis.md` | lane_summary, cs_at_minute |
| `docs/api/tools/pro-scene.md` | search_pro_player, search_team, get_pro_matches, get_league_matches, etc. |

## Per-tool section template

```markdown
## get_hero_performance

One-line purpose of what the tool answers.

\`\`\`python
result = await client.call_tool("get_hero_performance", {
    "match_id": 8594217096,
    "hero": "pugna",
})
\`\`\`

**Returns:**

\`\`\`json
{ "...": "real-shaped JSON" }
\`\`\`
```

Also update `docs/api/tools/index.md`: add the tool to the "AI Summary - Tool Selection Guide"
admonition table and bump the per-category tool count in the Categories table. (The matching LLM
instruction in `dota_match_mcp_server.py::TOOL_INSTRUCTIONS` is updated by the `add-mcp-tool`
skill — keep both in sync.)

## Adding a NEW page

The nav in `mkdocs.yml` is fully manual — a page not listed under `nav:` 404s. Add it under the
right section (API Reference > Tools lists the five tool pages today). Editing under `docs/**` or
`mkdocs.yml` is what makes `docs.yml` redeploy.

## Style conventions (match existing pages)

- Top of a major page: a collapsible `??? info "AI Summary"` admonition summarizing the page.
- Use `!!! note`, `!!! info`, `??? info` admonitions; fenced code via pymdownx superfences.
- Resource IDs use the `dota2://` namespace (e.g. `dota2://heroes/all`); any regenerated JSON
  stays `lowercase_with_underscores`.

## TWO changelogs — do not confuse them

| File | Format | Edit it? |
|---|---|---|
| `docs/changelog.md` | Keep-a-Changelog (`## [1.2.0] - date`, `### Added/Changed`), user-facing, manual | YES — this is the per-change requirement |
| `CHANGELOG.md` (repo root) | commitizen-generated, conventional-commit (`## v1.1.0-dev5`, `### Feat/Fix`) | NO — auto-bumped by `cz bump`; don't hand-edit for routine docs |

For a normal docs/feature change, add a `### Added` (or Changed/Fixed) bullet under the current
version heading in `docs/changelog.md`.

## Deploy behavior (for context; do NOT run a build here)

`docs.yml` redeploys only on changes under `docs/**`, `mkdocs.yml`, or the workflow file. Push to
`master` runs `mike deploy --update-aliases master latest` + `mike set-default latest`; a
non-prerelease `v*` tag runs `mike deploy <version> latest` + set-default.

## HARD CONSTRAINT

Do NOT run `mkdocs build`/`mkdocs serve` or any build here. Verify statically: read `mkdocs.yml`
nav and the page you edited to confirm the entry exists and links resolve.
