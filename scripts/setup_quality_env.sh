#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
env_dir="$PWD/.venv-quality"
if [ ! -f "$env_dir/pyvenv.cfg" ]; then
    "${QUALITY_PYTHON:-python3}" -m venv "$env_dir"
fi
if ! grep -Eiq '^include-system-site-packages *= *false$' "$env_dir/pyvenv.cfg"; then
    echo "Quality environment must not inherit system packages." >&2
    exit 1
fi
constraints="$PWD/requirements/quality-constraints.txt"
extras="analysis,dev,quality"
if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
    if [ ! -x "$PREFIX/bin/ruff" ]; then
        echo "Install native Ruff with pkg install ruff first." >&2
        exit 1
    fi
    extras="analysis,dev,quality-termux"
    ln -sfn "$PREFIX/bin/ruff" "$env_dir/bin/ruff"
    "$env_dir/bin/ruff" --version
    # Expose only the native NumPy package and its distribution metadata.
    "$env_dir/bin/python" - "$PREFIX/bin/python" <<'PY'
import pathlib
import subprocess
import sys
import sysconfig

native = pathlib.Path(subprocess.check_output(
    [sys.argv[1], "-c", "import numpy; print(numpy.__file__)"], text=True
).strip()).parent
site = pathlib.Path(sysconfig.get_path("purelib"))
for source in [native, *native.parent.glob("numpy-*.dist-info"), *native.parent.glob("numpy.libs")]:
    target = site / source.name
    if target.is_symlink():
        target.unlink()
    if target.exists():
        raise SystemExit(f"Existing NumPy installation at {target}; recreate .venv-quality")
    target.symlink_to(source, target_is_directory=True)
PY
    native_version="$("$env_dir/bin/python" -c 'import numpy; print(numpy.__version__)')"
    constraints="$(mktemp "${TMPDIR:-$PREFIX/tmp}/musicforge-constraints.XXXXXX")"
    trap 'rm -f "$constraints"' EXIT
    grep -v '^numpy==' requirements/quality-constraints.txt > "$constraints"
    printf 'numpy==%s\n' "$native_version" >> "$constraints"
    echo "Using Termux native NumPy $native_version"
fi
"$env_dir/bin/python" -m pip --isolated install --upgrade -c "$constraints" -e ".[$extras]"
"$env_dir/bin/python" -m pip check

# Keep unsupported platforms usable for Python-only quality checks.
if [ "${QUALITY_SKIP_DOXYGEN:-0}" != 1 ]; then
    if [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] && [ -z "${TERMUX_VERSION:-}" ] && [[ "${PREFIX:-}" != */com.termux/files/usr ]]; then
        bash scripts/install_quality_doxygen.sh
    else
        echo "Skipping automatic Doxygen provisioning on this platform; use CI for documentation checks."
    fi
fi
