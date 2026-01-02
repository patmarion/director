#!/usr/bin/env bash
set -uo pipefail

# run tests from the root of the repository
cd "$(dirname "${BASH_SOURCE[0]}")/.."

FAILED=0

for PYTHON_VERSION in 3.10.19 3.12.12; do
  for QT_FLAVOR in pyside pyqt; do
    echo
    echo "=== Running tests: python=${PYTHON_VERSION}, qt=${QT_FLAVOR} ==="

    if ! uv sync --python "${PYTHON_VERSION}" --extra "${QT_FLAVOR}" --extra extras --extra test; then
      echo "FAILED: uv sync (python=${PYTHON_VERSION}, qt=${QT_FLAVOR})" >&2
      FAILED=1
      continue
    fi

    if ! xvfb-run uv run pytest; then
      echo "FAILED: pytest (python=${PYTHON_VERSION}, qt=${QT_FLAVOR})" >&2
      FAILED=1
    fi
  done
done

exit "${FAILED}"


