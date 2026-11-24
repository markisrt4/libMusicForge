# Contributing to libMusicForge

Thanks for helping build libMusicForge. You can start with a documentation fix,
a repeatable test, or an improvement to an adapter you already use.

## Finding something to work on

Search the existing interfaces, implementations, examples and tests before
adding a new abstraction. Open an issue to discuss substantial design
changes. Explain the use case, affected services or hardware, and how
someone else could reproduce the result.

## Setting up a development environment

From a checkout of your feature branch, use Python 3.11 or later:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[analysis]'
deactivate
bash scripts/setup_quality_env.sh
bash scripts/dev_check.sh --all
```

The isolated quality environment uses pinned constraints. Use `--test` for pytest, `--format` to apply Ruff fixes, and `--build` for packaging. `--all` runs static checks only. The pull-request workflows run pytest on Python 3.11–3.13, along with lint,
type and packaging checks. The manually dispatched full gate also checks Ruff, mypy and packaging.

## A quick architecture tour

Start with the [architecture guide](docs/architecture.md) to see where
contracts, adapters and application responsibilities belong. Reuse an
existing contract when it fits the capability being added. Keep device
and service dependencies at the adapter boundary.

## Where tests belong

- `tests/` holds unattended pytest tests. Use focused unit tests for isolated
  behavior and integration tests for boundaries between real library
  components. Existing coverage includes provider response parsing, identity resolution, playback sources and PCM analysis.
- `component_test/` holds manual checks. See the
  [component test guide](component_test/README.md) for the command,
  prerequisites and expected result.
- `examples/` holds usage examples. Link existing scripts from the
  component test guide when the same command also verifies a real setup.

Use mocked HTTP and synthetic PCM. Keep metric units and provider IDs intact. Document credential variables without including real credentials.

## Public interfaces and documentation

Annotate public Python APIs. Document inputs, units, outputs, failure
behavior and optional dependencies alongside the interface. Use Mermaid
for architecture, data flow and sequences. Update the README, relevant
design guide and affected example commands with behavior changes.

## Preparing a pull request

Work on a feature branch. Explain what changed, how to reproduce it,
which checks passed and which ones need hardware or a live service.
Remove private data and credentials from logs, preserve existing license
notices, and follow [AGENTS.md](AGENTS.md) for repository-specific checks.

On Termux, install `python-numpy` with `pkg` before quality setup. The setup
script links the native NumPy package and metadata into the isolated environment
and constrains pip to that installed version. Ubuntu CI retains its pinned NumPy
versions. Other system packages remain isolated.

Termux also requires native `ruff` (`pkg install ruff`). The quality setup
uses that executable instead of compiling Ruff with pip. Its version may
differ from the pinned CI version; CI remains authoritative.

On Termux, the checker passes `--no-native-parser` to mypy to avoid the
incompatible ast_serialize extension. Strict typing remains enabled. Both
`--lint` and `--all` enforce Ruff formatting.
