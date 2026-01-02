#!/usr/bin/env bash
set -uo pipefail

# check formatting and linting from the root of the repository
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run ruff format --check .
ruff_format_status=$?

uv run ruff check .
ruff_check_status=$?
set -e

if [[ $ruff_format_status -ne 0 || $ruff_check_status -ne 0 ]]; then
  exit 1
fi