"""Shared mental-model mode configuration."""

import os

VALID_SMM_MODES = {"baseline", "treatment"}


def smm_mode() -> str:
    """Return the active shared mental-model mode."""
    raw_mode = os.getenv("SIM_SMM_MODE")
    if raw_mode is None or not raw_mode.strip():
        raise ValueError("Missing required SIM_SMM_MODE.")

    mode = raw_mode.strip().lower()
    if mode not in VALID_SMM_MODES:
        valid = ", ".join(sorted(VALID_SMM_MODES))
        raise ValueError(
            f"Unsupported SIM_SMM_MODE={mode!r}. Expected one of: {valid}."
        )
    return mode


def explicit_smm_memory_enabled() -> bool:
    """Return whether explicit shared mental-model memory is enabled."""
    return smm_mode() == "treatment"


def smm_metadata() -> dict[str, object]:
    """Return stable metadata fields for the active SMM mode."""
    mode = smm_mode()
    return {
        "smm_mode": mode,
        "explicit_smm_memory": mode == "treatment",
    }
