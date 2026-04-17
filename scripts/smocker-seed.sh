#!/usr/bin/env bash
# Seed Smocker scenarios from YAML files.
# Usage: ./scripts/smocker-seed.sh [scenarios_dir]
# Default dir: frontend/e2e/fixtures/smocker
#
# See delivery/specs/smocker-patterns.md for the scenario format.

set -euo pipefail

SMOCKER_ADMIN="${SMOCKER_ADMIN:-http://localhost:8101}"
SCENARIOS_DIR="${1:-frontend/e2e/fixtures/smocker}"

if [[ ! -d "$SCENARIOS_DIR" ]]; then
  echo "⚠️  Smocker scenarios dir not found: $SCENARIOS_DIR"
  echo "Create it and add <source>.<scenario>.yml files — see delivery/specs/smocker-patterns.md"
  exit 0
fi

shopt -s nullglob
yaml_files=("$SCENARIOS_DIR"/*.yml)
if [[ ${#yaml_files[@]} -eq 0 ]]; then
  echo "No YAML scenarios in $SCENARIOS_DIR — skipping seed."
  exit 0
fi

echo "Resetting Smocker…"
curl -sSf -X POST "${SMOCKER_ADMIN}/reset" >/dev/null

for yaml in "${yaml_files[@]}"; do
  echo "Seeding ${yaml}…"
  curl -sSf -X POST "${SMOCKER_ADMIN}/mocks" \
    -H "Content-Type: application/x-yaml" \
    --data-binary "@${yaml}" >/dev/null
done

echo "Smocker seeded (${#yaml_files[@]} files)."
