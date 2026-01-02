#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "--- Docker Build"
docker/docker.py build
echo "--- Run Tests"
docker/docker.py run --root --headless -- bash docker/pytest_xvfb.sh
