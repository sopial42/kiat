#!/usr/bin/env bash
# Block until Smocker admin API responds, or timeout after 30s.

set -euo pipefail

SMOCKER_ADMIN="${SMOCKER_ADMIN:-http://localhost:8101}"
TIMEOUT=30
START=$(date +%s)

echo -n "Waiting for Smocker at ${SMOCKER_ADMIN}..."
while true; do
  if curl -sSf -o /dev/null "${SMOCKER_ADMIN}/version"; then
    echo " ready."
    exit 0
  fi
  NOW=$(date +%s)
  if (( NOW - START > TIMEOUT )); then
    echo " TIMEOUT after ${TIMEOUT}s."
    exit 1
  fi
  echo -n "."
  sleep 1
done
