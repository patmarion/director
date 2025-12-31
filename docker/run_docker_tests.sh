#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"


./docker.py build
./docker.py run --root --headless -- bash /workdir/docker/pytest_xvfb.sh
