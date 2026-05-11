"""Load task context and expose task-level constants."""

import json
from pathlib import Path
from typing import Iterable

TASK_PATH = Path(__file__).parent / "hidden_profile_task.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_KEYS = ("agent_1", "agent_2", "agent_3")


def load_task() -> dict:
    """Load the hidden-profile task definition from the local JSON file."""
    with TASK_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _task_config_error(message: str) -> ValueError:
    """Build a clear startup error for invalid task configuration."""
    return ValueError(f"Invalid task config in {TASK_PATH}: {message}")


def _require_non_empty_string(task: dict, key: str) -> str:
    """Return a required non-empty string field."""
    value = task.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _task_config_error(f"{key!r} must be a non-empty string.")
    return value


def _require_string_list(task: dict, key: str) -> list[str]:
    """Return a required list containing only non-empty strings."""
    value = task.get(key)
    if not isinstance(value, list):
        raise _task_config_error(f"{key!r} must be a list of strings.")
    if not value:
        raise _task_config_error(f"{key!r} must not be empty.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise _task_config_error(f"{key!r} must contain only non-empty strings.")
    return value


def _validate_task(task: object) -> dict:
    """Validate experiment task invariants once at startup."""
    if not isinstance(task, dict):
        raise _task_config_error("top-level JSON value must be an object.")

    _require_non_empty_string(task, "goal")
    candidates = _require_string_list(task, "candidates")
    _require_string_list(task, "public_information")

    private_information = task.get("private_information")
    if not isinstance(private_information, dict):
        raise _task_config_error("'private_information' must be an object.")

    configured_agent_keys = set(private_information)
    expected_agent_keys = set(AGENT_KEYS)
    if configured_agent_keys != expected_agent_keys:
        raise _task_config_error(
            "'private_information' must contain exactly these agents: "
            f"{', '.join(AGENT_KEYS)}."
        )

    for agent_key in AGENT_KEYS:
        _require_string_list(private_information, agent_key)

    correct_candidate = _require_non_empty_string(task, "correct_candidate")
    if correct_candidate not in candidates:
        raise _task_config_error(
            "'correct_candidate' must be one of the configured candidates."
        )

    return task


TASK = _validate_task(load_task())


def _as_bullets(items: Iterable[str]) -> str:
    """Render an iterable of strings as markdown bullets, or a placeholder if empty."""
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def get_correct_candidate() -> str:
    """Return the validated task ground-truth candidate."""
    return TASK["correct_candidate"]
