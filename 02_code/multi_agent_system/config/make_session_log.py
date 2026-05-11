"""Create the per-run raw output directory and session log file."""

import json
import os
import re
import time
from pathlib import Path

from .smm import smm_metadata, smm_mode

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_SIMULATIONS_DIR = REPO_ROOT / "01_data" / "raw" / "simulations"

TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")


def _get_config_value(key: str, default: str) -> str:
    """Return a configured environment value."""
    return os.getenv(key) or default


def _safe_path_part(value: str, default: str) -> str:
    """Normalize a config value so it is safe as one path segment."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return cleaned or default


RUN_TAG = _safe_path_part(_get_config_value("SIM_RUN_TAG", "run"), "run")
SIM_CONDITION = _safe_path_part(
    _get_config_value("SIM_CONDITION", "unknown").lower(),
    "unknown",
)
SIM_SMM_MODE = _safe_path_part(smm_mode(), "treatment")
DEFAULT_RUN_ID = (
    f"{SIM_CONDITION}_{SIM_SMM_MODE}_{RUN_TAG}_{TIMESTAMP}"
    if RUN_TAG != "run"
    else f"{SIM_CONDITION}_{SIM_SMM_MODE}_{TIMESTAMP}"
)
RUN_ID = _safe_path_part(_get_config_value("SIM_RUN_ID", DEFAULT_RUN_ID), DEFAULT_RUN_ID)

RUN_DIR = RAW_SIMULATIONS_DIR / SIM_CONDITION / RUN_ID
LOG_DIR = RUN_DIR
SESSION_LOG_FILE = RUN_DIR / "session.log"
METADATA_FILE = RUN_DIR / "metadata.json"
CHAT_LOG_FILE = RUN_DIR / "chat.md"
SHARED_MENTAL_MODELS_DIR = RUN_DIR / "shared_mental_models"


def _base_metadata() -> dict:
    """Return stable metadata fields known when the run starts."""
    return {
        "schema_version": 1,
        "status": "initialized",
        "run_id": RUN_ID,
        "condition": SIM_CONDITION,
        **smm_metadata(),
        "run_tag": RUN_TAG,
        "timestamp": TIMESTAMP,
        "paths": {
            "run_dir": str(RUN_DIR),
            "session_log": str(SESSION_LOG_FILE),
            "chat": str(CHAT_LOG_FILE),
            "shared_mental_models": str(SHARED_MENTAL_MODELS_DIR),
        },
    }


def _write_metadata(metadata: dict) -> None:
    """Persist run metadata in a deterministic JSON format."""
    METADATA_FILE.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def update_run_metadata(updates: dict) -> None:
    """Merge updates into metadata.json for the current run."""
    metadata = _base_metadata()
    if METADATA_FILE.exists():
        try:
            metadata.update(json.loads(METADATA_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass

    metadata.update(_base_metadata())
    metadata.update(updates)
    _write_metadata(metadata)


RUN_DIR.mkdir(parents=True, exist_ok=True)
SESSION_LOG_FILE.write_text("", encoding="utf-8")
CHAT_LOG_FILE.write_text("# Public Discussion\n\n", encoding="utf-8")
_write_metadata(_base_metadata())
