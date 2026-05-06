#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"

REMOTE_REPO="${SIM_REMOTE_REPO:-~/git/bachelor_thesis}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

echo "Starting local simulation batch on this server: $BATCH_ID"

cd "$REMOTE_REPO"
git reset --hard HEAD
git clean -fd 01_data/raw/simulations
git pull --ff-only
source adk/bin/activate

mkdir -p logs

nohup bash -lc "SIM_BATCH_ID=$BATCH_ID ./02_code/simulation_scripts/run_all_conditions.sh" \
  > "logs/simulation_${BATCH_ID}.log" 2>&1 < /dev/null &

echo "Started detached simulation batch: $BATCH_ID"
echo "Log file: $REMOTE_REPO/logs/simulation_${BATCH_ID}.log"

echo
echo "Simulation started: $BATCH_ID"
echo "This server session can now disconnect."
echo
echo "Check progress with:"
echo "tail -f $REMOTE_REPO/logs/simulation_${BATCH_ID}.log"
echo
echo "Fetch results later from your Mac with:"
echo "rsync -avh --progress HohServer:$REMOTE_REPO/01_data/raw/simulations/ \"$LOCAL_REPO/01_data/raw/simulations/\""