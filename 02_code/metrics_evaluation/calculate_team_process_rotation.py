#!/usr/bin/env python3
"""Calculate team-process metrics for the A/C label-rotated task."""

from __future__ import annotations

import sys
from typing import Any

import calculate_team_process as base


def _swap_ac_candidate_labels(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return fact definitions with Candidate A and C labels swapped."""
    swapped = []
    for fact in facts:
        copy = dict(fact)
        candidate = copy.get("candidate")
        if candidate == "A":
            copy["candidate"] = "C"
        elif candidate == "C":
            copy["candidate"] = "A"
        swapped.append(copy)
    return swapped


base.TEAM_PROCESS_METHOD = "rotated_ac_private_uptake_integration_v3"
base.PRIVATE_FACTS = _swap_ac_candidate_labels(base.PRIVATE_FACTS)


def main() -> int:
    """Run the base team-process calculator with A/C-swapped fact labels."""
    return base.main()


if __name__ == "__main__":
    sys.exit(main())
