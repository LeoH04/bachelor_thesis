import json
import logging
import os
import time
from pathlib import Path
from itertools import count

# Path: config/trace.py -> parent -> multi_agent_system -> parent -> 02_code
log_dir = Path(__file__).parent.parent.parent / "metrics"
log_dir.mkdir(parents=True, exist_ok=True)

run_tag = os.getenv("SIM_RUN_TAG", "run")
timestamp = time.strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"trace_{run_tag}_{timestamp}.log"

logger = logging.getLogger("trace")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file, mode="w")
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)

_event_counter = count(1)


def _truncate_text(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def log_event(event_type: str, **data: object) -> None:
    payload: dict[str, object] = {
        "id": next(_event_counter),
        "ts": time.time(),
        "event": event_type,
    }
    payload.update(data)
    logger.info(json.dumps(payload, ensure_ascii=True))
