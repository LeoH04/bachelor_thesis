"""Create the per-run raw output directory and session log file."""

import json
import os
import re
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RAW_SIMULATIONS_DIR = REPO_ROOT / "01_data" / "raw" / "simulations"
ENV_FILES = (REPO_ROOT / ".env", PACKAGE_ROOT / ".env")

TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")


def _read_env_file_value(path: Path, key: str) -> str | None:
    """Read one key from a simple .env file without mutating process env."""
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()

        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            return value.strip().strip("\"'")

    return None


def _get_config_value(key: str, default: str) -> str:
    """Return env var value, falling back to repo/package .env files."""
    value = os.getenv(key)
    if value:
        return value

    for env_file in ENV_FILES:
        value = _read_env_file_value(env_file, key)
        if value:
            return value

    return default


def _safe_path_part(value: str, default: str) -> str:
    """Normalize a config value so it is safe as one path segment."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return cleaned or default


RUN_TAG = _safe_path_part(_get_config_value("SIM_RUN_TAG", "run"), "run")
SIM_CONDITION = _safe_path_part(
    _get_config_value("SIM_CONDITION", "unknown").lower(),
    "unknown",
)
DEFAULT_RUN_ID = (
    f"{SIM_CONDITION}_{RUN_TAG}_{TIMESTAMP}"
    if RUN_TAG != "run"
    else f"{SIM_CONDITION}_{TIMESTAMP}"
)
RUN_ID = _safe_path_part(_get_config_value("SIM_RUN_ID", DEFAULT_RUN_ID), DEFAULT_RUN_ID)

RUN_DIR = RAW_SIMULATIONS_DIR / SIM_CONDITION / RUN_ID
LOG_DIR = RUN_DIR
SESSION_LOG_FILE = RUN_DIR / "session.log"
METADATA_FILE = RUN_DIR / "metadata.json"
SHARED_MENTAL_MODELS_DIR = RUN_DIR / "shared_mental_models"


def _base_metadata() -> dict:
    """Return stable metadata fields known when the run starts."""
    return {
        "schema_version": 1,
        "status": "initialized",
        "run_id": RUN_ID,
        "condition": SIM_CONDITION,
        "run_tag": RUN_TAG,
        "timestamp": TIMESTAMP,
        "paths": {
            "run_dir": str(RUN_DIR),
            "session_log": str(SESSION_LOG_FILE),
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
_write_metadata(_base_metadata())
