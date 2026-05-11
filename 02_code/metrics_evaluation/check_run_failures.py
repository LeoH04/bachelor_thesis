#!/usr/bin/env python3
"""List simulation runs with failures or warnings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"


def read_metadata(path: Path) -> dict:
    """Read one metadata file."""
    return json.loads(path.read_text(encoding="utf-8"))


def warning_codes(metadata: dict) -> str:
    """Return a compact comma-separated warning-code summary."""
    warnings = metadata.get("warnings") or []
    codes = [str(item.get("code", "unknown")) for item in warnings if isinstance(item, dict)]
    return ", ".join(codes) if codes else "warning_count_without_details"


def problem_summary(path: Path) -> str | None:
    """Return a problem summary for one metadata file, or None if clean."""
    try:
        metadata = read_metadata(path)
    except Exception as exc:
        return f"BROKEN_METADATA: {exc}"
    if not isinstance(metadata, dict):
        return "BROKEN_METADATA: top-level JSON value is not an object"

    status = metadata.get("status", "missing")
    warnings = metadata.get("warnings") or []
    warning_count = metadata.get("warning_count") or 0
    if not isinstance(warning_count, int):
        warning_count = len(warnings)
    if not warning_count and warnings:
        warning_count = len(warnings)

    problems = []
    if status != "completed":
        problems.append(f"status={status}")
        failure_reason = metadata.get("failure_reason")
        if failure_reason:
            problems.append(f"failure_reason={failure_reason}")
    if warning_count:
        problems.append(f"warnings={warning_count} [{warning_codes(metadata)}]")

    return "; ".join(problems) if problems else None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="List simulation metadata files with failures or warnings."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    """Scan metadata files and print a compact report."""
    args = parse_args()
    metadata_paths = sorted(args.input_root.glob("**/metadata.json"))
    problems = []

    for path in metadata_paths:
        summary = problem_summary(path)
        if summary:
            problems.append((path, summary))

    print(f"Scanned metadata files: {len(metadata_paths)}")
    print(f"Runs with failures or warnings: {len(problems)}")

    for path, summary in problems:
        try:
            relative_path = path.resolve().relative_to(REPO_ROOT)
        except ValueError:
            relative_path = path
        print(f"- {relative_path}: {summary}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
