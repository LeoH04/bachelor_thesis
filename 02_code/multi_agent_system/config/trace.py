"""Structured JSON-line event tracing for simulation runs."""

import json
import logging
import time
from itertools import count

from .make_session_log import SESSION_LOG_FILE

logger = logging.getLogger("trace")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(SESSION_LOG_FILE, mode="a")
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)

_event_counter = count(1)


def _truncate_text(value: str, limit: int = 500) -> str:
    """Return a shortened preview string for verbose trace fields."""
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def log_event(event_type: str, **data: object) -> None:
    """Append one structured trace event to the unified session log."""
    payload: dict[str, object] = {
        "id": next(_event_counter),
        "ts": time.time(),
        "event": event_type,
    }
    payload.update(data)
    logger.info(json.dumps(payload, ensure_ascii=True))
