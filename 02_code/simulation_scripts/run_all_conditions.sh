#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CODE_DIR="$REPO_ROOT/02_code"
CALLER_SIM_SMM_MODE="${SIM_SMM_MODE:-}"
CALLER_SIM_BATCH_ID="${SIM_BATCH_ID:-}"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

if [[ -n "$CALLER_SIM_SMM_MODE" ]]; then
  SIM_SMM_MODE="$CALLER_SIM_SMM_MODE"
fi

if [[ -n "$CALLER_SIM_BATCH_ID" ]]; then
  SIM_BATCH_ID="$CALLER_SIM_BATCH_ID"
fi

COUNT="${SIM_COUNT:-10}"
SKIP_COMPLETED="${SIM_SKIP_COMPLETED:-1}"
RUN_TAG="${SIM_RUN_TAG:-transparency_experiment}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"
if [[ -n "${SIM_SMM_MODE:-}" ]]; then
  SMM_MODES=("$SIM_SMM_MODE")
else
  SMM_MODES=(treatment baseline)
fi

for smm_mode in "${SMM_MODES[@]}"; do
  case "$smm_mode" in
    baseline|treatment) ;;
    *)
      echo "Unsupported SIM_SMM_MODE: $smm_mode" >&2
      echo "Expected one of: baseline, treatment" >&2
      exit 1
      ;;
  esac
done

cd "$CODE_DIR"

for smm_mode in "${SMM_MODES[@]}"; do
  for condition in low moderate high; do
    echo "Running condition: $condition ($smm_mode)"

    for i in $(seq -f "%03g" 1 "$COUNT"); do
      run_id="${condition}_${smm_mode}_${BATCH_ID}_${i}"
      metadata_file="$REPO_ROOT/01_data/raw/simulations/$condition/$run_id/metadata.json"

      if [[ "$SKIP_COMPLETED" == "1" && -f "$metadata_file" ]] \
        && grep -q '"status": "completed"' "$metadata_file"; then
        echo "Skipping completed simulation $i/$COUNT: $run_id"
        continue
      fi

      echo "Starting simulation $i/$COUNT: $run_id"

      if SIM_CONDITION="$condition" \
        SIM_SMM_MODE="$smm_mode" \
        SIM_RUN_ID="$run_id" \
        SIM_RUN_TAG="$RUN_TAG" \
        adk run multi_agent_system --replay multi_agent_system/config/replay.json; then
        if ! grep -q '"status": "completed"' "$metadata_file"; then
          echo "Simulation did not complete successfully: $run_id" >&2
          exit 1
        fi

        echo "Finished simulation $i/$COUNT: $run_id"
      else
        status=$?
        echo "Simulation failed: $run_id" >&2
        exit "$status"
      fi
    done

    echo "Finished condition: $condition ($smm_mode)"
  done

  echo "Finished all conditions for batch: $BATCH_ID ($smm_mode)"
done

echo "Finished SMM simulations for batch: $BATCH_ID"
