#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

COUNT="${SIM_COUNT:-10}"
RUN_TAG="${SIM_RUN_TAG:-transparency_experiment}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

for condition in low moderate high; do
  echo "Running condition: $condition"

  SIM_CONDITION="$condition" \
    SIM_COUNT="$COUNT" \
    SIM_RUN_TAG="$RUN_TAG" \
    SIM_BATCH_ID="$BATCH_ID" \
    "$SCRIPT_DIR/run_10_simulations.sh"

  echo "Finished condition: $condition"
done

echo "Finished all conditions for batch: $BATCH_ID"
