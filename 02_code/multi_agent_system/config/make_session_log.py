"""Create the per-run unified session log file for simulation output."""

import os
import time
from pathlib import Path

# Store experimental session logs as raw data at the repository root.
LOG_DIR = Path(__file__).resolve().parents[3] / "01_data" / "raw" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_TAG = os.getenv("SIM_RUN_TAG", "run")
TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
SESSION_LOG_FILE = LOG_DIR / f"session_{RUN_TAG}_{TIMESTAMP}.log"

# Ensure each process/session starts with one fresh unified log file.
SESSION_LOG_FILE.write_text("", encoding="utf-8")
