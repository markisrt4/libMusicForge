#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
mode="${1:---all}"
case "$mode" in
    --all|--lint|--format|--types|--test|--build|--docs) ;;
    *) echo "Usage: bash scripts/dev_check.sh [--all|--lint|--format|--types|--test|--build|--docs]" >&2; exit 2 ;;
esac
if [ "$#" -gt 0 ]; then shift; fi
if [ ! -x .venv-quality/bin/python ]; then
    echo "Run bash scripts/setup_quality_env.sh first." >&2
    exit 1
fi
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
source .venv-quality/bin/activate
mypy_args=(--no-incremental)
if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
    log="$(mktemp "${TMPDIR:-$PREFIX/tmp}/musicforge-diagnostic.XXXXXX")" || exit 1
    trap 'rm -f "$log"' EXIT
    temporary_log=1
    mypy_args+=(--no-native-parser)
else
    log_dir="${XDG_CACHE_HOME:-$HOME/.cache}/musicforge"
    mkdir -p "$log_dir" || exit 1
    log="$log_dir/dev-check.log"
    temporary_log=0
fi
run_checks() {
    local rc=0
    echo "=== Python environment ==="
    command -v python
    python -c 'from pathlib import Path; import musicforge; p = Path(musicforge.__file__).resolve(); print(p); assert p.is_relative_to(Path("src").resolve()), "Not importing checkout"' || return 1
    if [ "$#" -eq 0 ]; then set -- src tests; fi
    if [ "$mode" = --all ] || [ "$mode" = --lint ]; then
        ruff check "$@" || rc=1
        ruff format --check "$@" || rc=1
    fi
    if [ "$mode" = --format ]; then
        ruff check --fix "$@" || rc=1
        ruff format "$@" || rc=1
    fi
    if [ "$mode" = --all ] || [ "$mode" = --types ]; then
        python -m mypy "${mypy_args[@]}" || rc=1
    fi
    if [ "$mode" = --test ]; then
        python -m pytest -q || rc=1
    fi
    if [ "$mode" = --docs ]; then
        if ! command -v doxygen >/dev/null 2>&1; then
            echo "Doxygen 1.15.0 required; use Ubuntu CI or install it locally." >&2
            return 1
        fi
        if ! doxygen --version | grep -Eq '^1\.15\.0([[:space:]]|$)'; then
            echo "Doxygen 1.15.0 required." >&2
            return 1
        fi
        mkdir -p build/doxygen && doxygen Doxyfile || rc=1
    fi
    if [ "$mode" = --build ]; then
        python -m build || rc=1
    fi
    return "$rc"
}
run_checks "$@" 2>&1 | tee "$log"
rc=$?
if [ "$rc" -ne 0 ]; then
    if command -v termux-clipboard-set >/dev/null 2>&1; then
        timeout 5 termux-clipboard-set < "$log" || true
    elif [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wl-copy >/dev/null 2>&1; then
        wl-copy < "$log" || true
    elif [ -n "${DISPLAY:-}" ] && command -v xclip >/dev/null 2>&1; then
        xclip -selection clipboard < "$log" || true
    fi
fi
if [ "$temporary_log" -eq 0 ]; then echo "Log saved to $log"; fi
exit "$rc"
