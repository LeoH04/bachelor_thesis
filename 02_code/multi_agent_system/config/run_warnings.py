"""Record non-fatal warnings that may affect simulation data quality."""

from __future__ import annotations

import json
import time
from typing import Any

WARNINGS_KEY = "warnings"
WARNING_COUNT_KEY = "warning_count"


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable value, or a readable fallback."""
    try:
        json.dumps(value)
    except TypeError:
        return repr(value)
    return value


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    """Return details normalized for metadata JSON output."""
    return {key: _json_safe(value) for key, value in details.items()}


def build_run_warning(code: str, message: str, **details: Any) -> dict[str, Any]:
    """Build one warning record for metadata and trace output."""
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "code": str(code),
        "message": str(message),
        "details": _safe_details(details),
    }


def merge_run_warning(metadata: dict[str, Any], warning: dict[str, Any]) -> None:
    """Append a warning to run metadata in place."""
    warnings = metadata.get(WARNINGS_KEY)
    if not isinstance(warnings, list):
        warnings = []

    warnings.append(warning)
    metadata[WARNINGS_KEY] = warnings
    metadata[WARNING_COUNT_KEY] = len(warnings)


def log_run_warning_event(warning: dict[str, Any]) -> None:
    """Write the warning to the structured trace log when tracing is available."""
    try:
        from .trace import log_event

        log_event("run_warning", **warning)
    except Exception:
        # Warning recording must never make the simulation fail.
        pass


def record_run_warning(code: str, message: str, **details: Any) -> dict[str, Any]:
    """Append a non-fatal run warning to metadata and session trace output."""
    warning = build_run_warning(code, message, **details)
    warnings_to_log = []

    from .make_session_log import (
        METADATA_FILE,
        _METADATA_LOCK,
        _base_metadata,
        _write_metadata,
    )

    with _METADATA_LOCK:
        metadata = _base_metadata()
        if METADATA_FILE.exists():
            try:
                metadata.update(json.loads(METADATA_FILE.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                corrupt_warning = build_run_warning(
                    "run_metadata_json_malformed",
                    "Existing run metadata could not be parsed and was rebuilt.",
                    error=str(exc),
                    metadata_file=str(METADATA_FILE),
                )
                merge_run_warning(metadata, corrupt_warning)
                warnings_to_log.append(corrupt_warning)

        metadata.update(_base_metadata())
        merge_run_warning(metadata, warning)
        _write_metadata(metadata)

    for item in warnings_to_log:
        log_run_warning_event(item)
    log_run_warning_event(warning)
    return warning
