#!/usr/bin/env bash
set -u
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

PYTHON_CMD=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) else 1)' >/dev/null 2>&1; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "ERROR: Python 3.11, 3.12, or 3.13 was not found." >&2
    echo "Ubuntu/Debian example: sudo apt update && sudo apt install -y python3 python3-venv python3-tk" >&2
    exit 1
fi

"$PYTHON_CMD" bootstrap.py "$@"
