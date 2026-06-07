---
name: release-version
description: >-
  Cuts a release of the mcp-replay-dota2 Dota 2 MCP server. Use whenever the user wants to release
  a new version, cut/ship a release, bump the version, publish to PyPI/TestPyPI, tag a release, or
  push a Docker image for this project. Encodes the strict tag==pyproject-version check, the PEP440
  prerelease routing (TestPyPI vs PyPI), the commitizen bump flow that keeps pyproject + CHANGELOG
  in sync, and the GitHub-release + Docker fan-out so a release is not pushed broken.
disable-model-invocation: true
allowed-tools: Bash(uv run cz *) Bash(git tag *) Bash(git push *) Bash(uv build) Bash(uv run ruff *) Bash(uv run mypy *)
---

# Release mcp-replay-dota2

`release.yml` is triggered ONLY by pushing a tag matching `v*`. It HARD-FAILS the build if the tag
version != `pyproject.toml [project].version`. Get these aligned before pushing or the whole run
dies.

Current version is `1.2.0` in BOTH `[project].version` AND `[tool.commitizen].version`. The
commitizen `version_files` is a single regex (`pyproject.toml:^version`) that matches BOTH
line-anchored `version` lines, so `cz bump` rewrites both at once — keep them aligned.

## Workflow

1. **Pick the version.** For a prerelease use a PEP440 suffix (`.dev`, `aN`, `bN`, `rcN`) — these
   route to TestPyPI, NOT PyPI. Stable versions go to PyPI + GitHub release + Docker.
2. **Bump with commitizen** (preferred — keeps `pyproject.toml` and `CHANGELOG.md` in sync and
   creates the `v$version` tag):
   ```bash
   uv run cz bump          # auto-detects bump from conventional commits
   # or force: uv run cz bump --increment PATCH|MINOR|MAJOR
   ```
   commitizen config: `cz_conventional_commits`, `tag_format=v$version`,
   `update_changelog_on_bump=true`, `changelog_file=CHANGELOG.md`, incremental. The single
   `version_files` regex rewrites both `[project].version` and `[tool.commitizen].version`.
3. **Verify tag == version** (release.yml does exactly this and exits 1 on mismatch):
   ```bash
   uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
   git describe --tags --abbrev=0
   ```
   The two must be identical (tag without the leading `v`).
4. **Run the local CI gate** — release.yml re-runs ruff + mypy before building, so failures there
   waste a tagged run:
   ```bash
   uv run ruff check src/ tests/ dota_match_mcp_server.py
   uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports
   uv run pytest
   ```
5. **Update `docs/changelog.md`** (Keep-a-Changelog, user-facing) for release notes if not already
   done. `CHANGELOG.md` is the commitizen-generated one — let `cz bump` own it.
6. **Push the tag** to trigger the release pipeline (only when the user asks to push):
   ```bash
   git push origin master
   git push origin v<version>
   ```
7. **Ad-hoc image only:** use the `docker-manual.yml` workflow (`workflow_dispatch`, input
   `version`) — pushes an image without a full release.

## What release.yml does after the tag push

1. `build` — `uv sync --group dev`, verify version==tag, ruff, mypy, `uv build` (hatchling),
   upload `dist/`.
2. `check-version` — sets `is_prerelease=true` if the version matches
   `([\.-]dev|a[0-9]|b[0-9]|rc[0-9])`.
3. Prerelease -> `publish-testpypi` (environment `testpypi`). Stable -> `publish-pypi`
   (environment `pypi`) THEN `github-release` (auto release notes) AND `docker-publish`.
4. Publishing uses PyPI Trusted Publishing (`id-token: write`, `pypa/gh-action-pypi-publish`) —
   no API tokens.
5. Docker image `dbcjuanma/mcp_replay_dota2` tagged `<version>` + `latest`, `linux/amd64` ONLY
   (arm64 was removed, commit 8415471), gha cache.

## Build facts

hatchling backend, `packages = ["src"]`, with a `force-include` of `dota_match_mcp_server.py`.
Console-script entry point: `dota-match-mcp-server = dota_match_mcp_server:main`.

## Gotchas

- A prerelease version pushed as a tag will NEVER hit PyPI/GitHub-release/Docker — it only reaches
  TestPyPI. If you intended a real release, don't use a `.dev/aN/bN/rcN` suffix.
- `test.yml` has `cancel-in-progress: false`, so the release-time push to master won't cancel an
  in-flight test run.
- HARD CONSTRAINT here: do not actually build/publish/push from this environment unless the user
  explicitly asks. Verify version alignment statically first.
