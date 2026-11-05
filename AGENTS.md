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

## Codex execution and CI cost policy

- Do **not** run tests, lint, type checks, builds, quality gates, benchmarks, or validation scripts in the Codex cloud VM by default. This includes indirect invocations via Make, Gradle, npm, shell scripts, pre-commit hooks, or other wrappers.
- Write and update meaningful tests alongside code changes, but delegate their execution to GitHub Actions. For device-dependent verification, give the user exact commands for their Linux, Raspberry Pi, or Android/Termux environment.
- Read GitHub Actions logs, statuses, and downloadable reports to diagnose failures. Make targeted fixes and push them for CI to rerun. Do not rerun tests in the agent VM simply because CI fails.
- Do not execute tests locally even when an existing repository instruction says to run focused checks. This section overrides such instructions for Codex cloud sessions. Static review of source and diffs without running validation tools is allowed.
- Only run a check in the Codex VM if the user **explicitly authorizes that specific execution**. General requests such as 'fix it', 'verify', or 'make sure it works' are not authorization to consume Codex cloud execution for tests.
- Clearly report which checks CI actually ran, which checks are pending, and which require physical hardware. Never imply unexecuted tests passed.
- Do not install dependencies in the Codex VM solely to run checks, tests, builds, or other validation. Dependency installation needed for actual implementation must be justified separately.
- Prefer concise CI failure summaries, JUnit XML artifacts, and the failing job's relevant log excerpt over reading entire workflow logs repeatedly.
- Request or inspect the GitHub Actions result for the exact commit before declaring verification complete. Use the workflow's manually dispatched full gate before merge where configured; do not claim the full gate ran just because fast CI passed.
