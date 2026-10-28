# AGENTS.md — libMusicForge development guide

These instructions apply to automated coding agents and contributors working in this repository.

## Mission and scope

Build a reusable, provider-agnostic **music metadata, statistics, and discovery library**, with an optional HTTP API. The library is the product; a server is an adapter. Do not add a GUI, music player, copyrighted audio distribution, or OpenRoadCode-specific dependencies.

## Before changing code

1. Inspect the current tree, README, tests, and existing conventions. Do not assume planned modules already exist.
2. Search for an existing implementation or abstraction before creating a new one.
3. Keep changes small and scoped; document assumptions and unresolved provider limitations.
4. Use a feature branch and pull request for substantive changes. Do not directly modify `main` unless explicitly instructed.

## Architecture

- Use a `src/musicforge/` Python package layout when implementation begins.
- Separate domain models, provider interfaces, adapters, core services, and optional API transport.
- Define interfaces by capability (metadata, search, statistics, discovery), not a mandatory universal provider base class.
- Keep the core importable and usable without FastAPI, an active server, or a database.
- Prefer async network I/O with explicit timeouts, rate limiting, and clear errors.
- Make credentials configurable through environment variables or explicit configuration; never commit tokens.
- Prefer MusicBrainz identifiers where available, but preserve source-native IDs and avoid assuming that one ID represents all editions or recordings.
- Preserve provenance, timestamps, units, and provider-specific meanings for statistics. Never label Last.fm scrobbles as Spotify streams.
- Do not scrape around provider restrictions or assume unavailable APIs/fields are accessible.
- Keep provider failures isolated when a partial response is useful; do not silently fabricate missing data.
- Cache responsibly according to provider terms; support operation without persistent storage where practical.
- Keep OpenRoadCode integrations in the OpenRoadCode repository or separate examples, not in the core package.

## Engineering standards

- Target a documented, currently supported Python version when packaging is introduced; do not invent version guarantees before tests exist.
- Add type hints for public APIs, clear docstrings for exported interfaces, and focused tests for new behavior.
- Use deterministic fixtures and mocked HTTP for unit tests. Live provider tests must be optional and clearly marked.
- Validate external responses and handle missing fields, ambiguous matches, quotas, timeouts, and errors.
- Avoid unnecessary dependencies and premature frameworks.
- Update README and examples whenever public behavior or setup changes.
- Never describe a planned feature as implemented.

## Verification and reporting

- Run the tests, linting, and type checks relevant to changed files when those tools are configured.
- Report the exact commands and results. If checks were not run, say so; never claim a passing test without evidence.
- Provide the branch name, commit SHA, changed files, and any remaining limitations when finishing work.
- Do not merge into `main` without explicit authorization.

## Initial milestones

1. Packaging and typed models.
2. Provider contracts and mocked tests.
3. MusicBrainz metadata adapter.
4. Last.fm statistics adapter.
5. Optional HTTP API and integration examples.

Favor correctness, traceability, and maintainability over adding features quickly.
