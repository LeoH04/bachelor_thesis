#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

SERVER="${SIM_SERVER:-HohServer}"
REMOTE_REPO="${SIM_REMOTE_REPO:-~/git/bachelor_thesis}"
BATCH_ID="${SIM_BATCH_ID:-$(date +%Y%m%d_%H%M%S)}"
SMM_MODE="${SIM_SMM_MODE:-}"
SMM_LABEL="${SMM_MODE:-treatment+baseline}"
RESUME="${SIM_RESUME:-1}"

if [[ -n "$SMM_MODE" ]]; then
  case "$SMM_MODE" in
    baseline|treatment) ;;
    *)
      echo "Unsupported SIM_SMM_MODE: $SMM_MODE" >&2
      echo "Expected one of: baseline, treatment" >&2
      exit 1
      ;;
  esac
fi

echo "Starting remote simulation batch on $SERVER: $BATCH_ID ($SMM_LABEL)"

ssh "$SERVER" bash -s -- "$REMOTE_REPO" "$BATCH_ID" "$SMM_MODE" "$RESUME" <<'REMOTE'
set -euo pipefail

REMOTE_REPO="$1"
BATCH_ID="$2"
SMM_MODE="${3:-}"
RESUME="${4:-1}"
SMM_LABEL="${SMM_MODE:-treatment+baseline}"

cd "$REMOTE_REPO"
git reset --hard HEAD
if [[ "$RESUME" == "1" ]]; then
  echo "Resume mode enabled: keeping existing simulation outputs"
else
  git clean -fd 01_data/raw/simulations
fi
git pull --ff-only
source adk/bin/activate

mkdir -p logs

RUN_CMD="SIM_BATCH_ID=$BATCH_ID"
if [[ -n "$SMM_MODE" ]]; then
  RUN_CMD="$RUN_CMD SIM_SMM_MODE=$SMM_MODE"
fi
RUN_CMD="$RUN_CMD ./02_code/simulation_scripts/run_all_conditions.sh"

nohup bash -lc "$RUN_CMD" \
  > "logs/simulation_${BATCH_ID}.log" 2>&1 < /dev/null &

echo "Started detached remote simulation batch: $BATCH_ID ($SMM_LABEL)"
echo "Log file: $REMOTE_REPO/logs/simulation_${BATCH_ID}.log"
REMOTE

echo "Remote simulation started: $BATCH_ID ($SMM_LABEL)"
echo "Your Mac can now sleep."
echo
echo "Check progress with:"
echo "ssh $SERVER 'tail -f $REMOTE_REPO/logs/simulation_${BATCH_ID}.log'"
echo
echo "Fetch results later with:"
echo "rsync -avh --progress $SERVER:$REMOTE_REPO/01_data/raw/simulations/ \"$LOCAL_REPO/01_data/raw/simulations/\""
