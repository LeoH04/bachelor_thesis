"""Input-context transparency configuration."""

import os

VALID_CONTEXT_TRANSPARENCY_CONDITIONS = {"low", "moderate", "high"}


def context_transparency_condition() -> str:
    """Return the active input-context transparency condition."""
    condition = os.getenv("SIM_CONDITION", "low").strip().lower()
    if condition not in VALID_CONTEXT_TRANSPARENCY_CONDITIONS:
        valid = ", ".join(sorted(VALID_CONTEXT_TRANSPARENCY_CONDITIONS))
        raise ValueError(
            f"Unsupported SIM_CONDITION={condition!r}. Expected one of: {valid}."
        )
    return condition


def current_round_history_enabled() -> bool:
    """Return whether prompts should see only current-round discussion history."""
    return False


def discussion_history_enabled() -> bool:
    """Return whether raw public discussion history should be shown in prompts."""
    return True


def thought_history_enabled() -> bool:
    """Return whether stored model thoughts should be shown in prompt history."""
    return context_transparency_condition() == "high"


def input_history_scope() -> str:
    """Return a stable metadata label for the prompt-visible history scope."""
    if context_transparency_condition() == "low":
        return "latest_turn"
    if not discussion_history_enabled():
        return "none"
    return "current_round" if current_round_history_enabled() else "full_history"


def smm_memory_scope() -> str:
    """Return a stable metadata label for the treatment memory scope."""
    return "full_meeting"


def context_transparency_metadata() -> dict[str, object]:
    """Return stable metadata fields for the input-transparency manipulation."""
    return {
        "context_transparency_condition": context_transparency_condition(),
    }
