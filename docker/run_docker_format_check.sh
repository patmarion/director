#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "--- Docker Build"
docker/docker.py build

echo "--- uv sync"
docker/docker.py run --root --headless -- uv sync --python 3.12 --extra test

echo "--- Ruff Format & Check"
docker/docker.py run --root --headless -- bash docker/format_check.sh
