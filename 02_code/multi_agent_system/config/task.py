"""Load task context and expose task-level constants."""

import json
from pathlib import Path
from typing import Iterable

TASK_PATH = Path(__file__).parent / "hidden_profile_task.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_task() -> dict:
    """Load the hidden-profile task definition from the local JSON file."""
    with TASK_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


TASK = load_task()


def _agent_sort_key(agent_key: str) -> tuple[str, int | str]:
    """Sort agent_N keys numerically while keeping a stable fallback."""
    prefix, separator, suffix = agent_key.rpartition("_")
    if separator:
        try:
            return prefix, int(suffix)
        except ValueError:
            pass
    return agent_key, agent_key


AGENT_KEYS = sorted(
    TASK.get("private_information", {}).keys(),
    key=_agent_sort_key,
)


def _as_bullets(items: Iterable[str]) -> str:
    """Render an iterable of strings as markdown bullets, or a placeholder if empty."""
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def get_correct_candidate() -> str | None:
    """Return the task's ground-truth candidate when configured."""
    candidate = TASK.get("correct_candidate") or TASK.get("optimal_candidate")
    if candidate in TASK.get("candidates", []):
        return str(candidate)
    return None
