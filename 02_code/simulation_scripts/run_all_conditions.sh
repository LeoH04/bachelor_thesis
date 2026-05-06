#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CODE_DIR="$REPO_ROOT/02_code"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

COUNT="${SIM_COUNT:-10}"
RUN_TAG="${SIM_RUN_TAG:-transparency_experiment}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

cd "$CODE_DIR"

for condition in low moderate high; do
  echo "Running condition: $condition"

  for i in $(seq -f "%03g" 1 "$COUNT"); do
    run_id="${condition}_${BATCH_ID}_${i}"
    echo "Starting simulation $i/$COUNT: $run_id"

    SIM_CONDITION="$condition" \
      SIM_RUN_ID="$run_id" \
      SIM_RUN_TAG="$RUN_TAG" \
      adk run multi_agent_system --replay multi_agent_system/config/replay.json

    echo "Finished simulation $i/$COUNT: $run_id"
  done

  echo "Finished condition: $condition"
done

echo "Finished all conditions for batch: $BATCH_ID"
