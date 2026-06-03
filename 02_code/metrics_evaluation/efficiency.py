#!/usr/bin/env python3
"""Calculate token efficiency and write it to simulation metadata files."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"


@dataclass
class RunMetric:
    """Completed run values needed for the condition-level efficiency metric."""

    path: Path
    metadata: dict
    group: str
    total_tokens: float
    decision_correct: float


def read_metadata(path: Path) -> dict:
    """Read one metadata.json file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_metadata(path: Path, metadata: dict) -> None:
    """Write one metadata.json file in the repository's standard format."""
    path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def metric_group(metadata: dict) -> str | None:
    """Return the comparison group used in the exploration plots."""
    if metadata.get("smm_mode") == "baseline":
        return "baseline"
    return metadata.get("context_transparency_condition") or metadata.get("condition")


def as_float(value: object) -> float | None:
    """Convert a metadata value to float, returning None for missing values."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_runs(input_root: Path) -> tuple[list[RunMetric], dict[str, int]]:
    """Collect completed runs with the fields needed for efficiency."""
    runs = []
    counts = {"included": 0, "incomplete": 0, "missing_fields": 0, "missing_group": 0}

    for path in sorted(input_root.glob("**/metadata.json")):
        metadata = read_metadata(path)
        if metadata.get("status") != "completed":
            counts["incomplete"] += 1
            continue

        group = metric_group(metadata)
        if not group:
            counts["missing_group"] += 1
            continue

        total_tokens = as_float(metadata.get("total_tokens"))
        decision_correct = as_float(metadata.get("decision_correct"))
        if total_tokens is None or decision_correct is None:
            counts["missing_fields"] += 1
            continue

        runs.append(
            RunMetric(
                path=path,
                metadata=metadata,
                group=str(group),
                total_tokens=total_tokens,
                decision_correct=decision_correct,
            )
        )
        counts["included"] += 1

    return runs, counts


def calculate_efficiency(runs: list[RunMetric]) -> dict[str, float | None]:
    """Calculate tokens per correct decision for each comparison group."""
    totals: dict[str, list[RunMetric]] = {}
    for run in runs:
        totals.setdefault(run.group, []).append(run)

    efficiency = {}
    for group, group_runs in totals.items():
        mean_tokens = sum(run.total_tokens for run in group_runs) / len(group_runs)
        correct_probability = (
            sum(run.decision_correct for run in group_runs) / len(group_runs)
        )
        efficiency[group] = (
            None
            if correct_probability == 0
            else round(mean_tokens / correct_probability, 2)
        )

    return efficiency


def update_metadata(input_root: Path) -> dict[str, int]:
    """Calculate efficiency and write it to all included metadata files."""
    runs, counts = collect_runs(input_root)
    efficiency = calculate_efficiency(runs)

    for run in runs:
        run.metadata["tokens_per_correct_decision"] = efficiency[run.group]
        write_metadata(run.path, run.metadata)

    counts["updated"] = len(runs)
    return counts


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate tokens per correct decision for simulation runs."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    """Calculate and persist the efficiency metric."""
    args = parse_args()
    counts = update_metadata(args.input_root)
    summary = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    print(f"Processed efficiency metrics ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())