#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

for smm_mode in treatment baseline; do
  echo "Running all transparency conditions for SMM mode: $smm_mode"

  SIM_BATCH_ID="$BATCH_ID" \
    SIM_SMM_MODE="$smm_mode" \
    "$SCRIPT_DIR/run_all_conditions.sh"

  echo "Finished SMM mode: $smm_mode"
done

echo "Finished treatment and baseline simulations for batch: $BATCH_ID"
