#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "--- Docker Build"
docker/docker.py build
echo "--- uv sync"
docker/docker.py run --root --headless -- uv sync --python 3.10.19 --all-extras
echo "--- Build Docs"
docker/docker.py run --root --headless -- bash docs/build.sh
echo "--- Creating Artifact"
tar -czf docs.tar.gz -C docs/_build/html .
