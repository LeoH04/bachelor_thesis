"""Load task context and expose task-level constants."""

import json
import os
from pathlib import Path
from typing import Iterable

TASK_VARIANT_RAW = os.getenv("SIM_TASK_VARIANT", "1").strip()
if TASK_VARIANT_RAW not in {"1", "2", "3"}:
    raise ValueError(
        f"Unsupported SIM_TASK_VARIANT={TASK_VARIANT_RAW!r}. Expected one of: 1, 2, 3."
    )

TASK_VARIANT = int(TASK_VARIANT_RAW)
TASK_PATH = Path(__file__).parent / "hidden_profile_task_1.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_task() -> dict:
    """Load the shared task definition and selected private-fact allocation."""
    with TASK_PATH.open("r", encoding="utf-8") as f:
        task = json.load(f)

    if TASK_VARIANT != 1:
        allocation_path = TASK_PATH.with_name(
            f"hidden_profile_task_{TASK_VARIANT}.json"
        )
        with allocation_path.open("r", encoding="utf-8") as f:
            task["private_information"] = json.load(f)

    return task


TASK = load_task()


def _require_candidates() -> list[str]:
    """Return configured candidates or fail before a simulation can run."""
    candidates = TASK.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Task config must set a non-empty candidates list.")
    if not all(isinstance(candidate, str) and candidate.strip() for candidate in candidates):
        raise ValueError("Task config candidates must be non-empty strings.")
    return candidates


CANDIDATES = _require_candidates()


def _require_correct_candidate() -> str:
    """Return the configured ground-truth candidate or fail before a run starts."""
    candidate = TASK.get("correct_candidate")
    if candidate is None:
        candidate = TASK.get("optimal_candidate")

    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("Task config must set correct_candidate to a configured candidate.")

    candidate = candidate.strip()
    if candidate not in CANDIDATES:
        valid = ", ".join(CANDIDATES)
        raise ValueError(
            f"Task config correct_candidate={candidate!r} is not a configured "
            f"candidate. Expected one of: {valid}."
        )

    return candidate


CORRECT_CANDIDATE = _require_correct_candidate()


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


def get_correct_candidate() -> str:
    """Return the task's required ground-truth candidate."""
    return CORRECT_CANDIDATE
