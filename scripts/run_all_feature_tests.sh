#!/usr/bin/env bash
# Run the complete repository test suite, including Solo Stack and visual-quality tests.
# Offline/default mode does not intentionally call paid providers or external APIs.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "ERROR: Python 3 was not found." >&2
  exit 2
fi

if ! "$PYTHON" -c 'import pytest' >/dev/null 2>&1; then
  echo "ERROR: pytest is not installed in $PYTHON." >&2
  echo "Install the project dev dependencies first (for example: uv sync --frozen)." >&2
  exit 2
fi

echo "Repository: $ROOT_DIR"
echo "Python: $("$PYTHON" --version 2>&1)"
if git -C "$ROOT_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  echo "Commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD)"
else
  echo "Commit: unavailable (not a Git checkout)"
fi
echo
echo "Running ALL automated tests in test/ and tests/."
echo "Live integrations remain opt-in; tests requiring unavailable services should skip."
echo

"$PYTHON" -X utf8 -m pytest -q --disable-warnings test tests
