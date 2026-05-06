#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"

SERVER="${SIM_SERVER:-HohServer}"
REMOTE_REPO="${SIM_REMOTE_REPO:-~/git/bachelor_thesis}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"

echo "Starting remote simulation batch on $SERVER: $BATCH_ID"

ssh "$SERVER" "bash -lc '
  set -euo pipefail
  cd $REMOTE_REPO
  git pull --ff-only
  source adk/bin/activate
  mkdir -p logs
  nohup bash -lc "SIM_BATCH_ID=$BATCH_ID ./02_code/simulation_scripts/run_all_conditions.sh; echo FINISHED_SUCCESSFULLY" \
  > logs/simulation_${BATCH_ID}.log 2>&1 < /dev/null &
  echo \"Started detached remote simulation batch: $BATCH_ID\"
  echo \"Log file: $REMOTE_REPO/logs/simulation_${BATCH_ID}.log\"
'"

echo "Remote simulation started: $BATCH_ID"
echo "Your Mac can now sleep."
echo
echo "Check progress with:"
echo "ssh $SERVER 'tail -f $REMOTE_REPO/logs/simulation_${BATCH_ID}.log'"
echo
echo "Fetch results later with:"
echo "rsync -avh --progress $SERVER:$REMOTE_REPO/01_data/raw/simulations/ \"$LOCAL_REPO/01_data/raw/simulations/\""