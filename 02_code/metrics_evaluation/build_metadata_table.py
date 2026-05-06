#!/usr/bin/env python3
"""Build a flat CSV table from simulation metadata files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"
DEFAULT_OUTPUT = REPO_ROOT / "01_data" / "processed" / "simulation_metrics.csv"

BASE_COLUMNS = [
    "run_id",
    "condition",
    "run_tag",
    "status",
    "timestamp",
    "completed_at",
    "rounds",
    "agent_turns",
    "agent_tool_calls",
    "agent_tool_messages",
    "memory_updates",
    "total_messages",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "runtime_seconds",
    "final_candidate",
    "decision_method",
    "correct_candidate",
    "decision_correct",
    "mean_pairwise_memory_similarity",
    "min_pairwise_memory_similarity",
    "max_pairwise_memory_similarity",
    "memory_similarity_method",
    "embedding_model",
    "metadata_file",
]

CONDITION_ORDER = {"low": 0, "moderate": 1, "high": 2}


def slug(value: object) -> str:
    """Convert labels like 'Candidate A' into stable CSV column parts."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def read_metadata(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def flatten_metadata(path: Path, metadata: dict) -> tuple[dict, set[str], set[str]]:
    context = metadata.get("context_consistency") or {}
    row = {
        "run_id": metadata.get("run_id"),
        "condition": metadata.get("condition"),
        "run_tag": metadata.get("run_tag"),
        "status": metadata.get("status"),
        "timestamp": metadata.get("timestamp"),
        "completed_at": metadata.get("completed_at"),
        "rounds": metadata.get("rounds"),
        "agent_turns": metadata.get("agent_turns"),
        "agent_tool_calls": metadata.get("agent_tool_calls"),
        "agent_tool_messages": metadata.get("agent_tool_messages"),
        "memory_updates": metadata.get("memory_updates"),
        "total_messages": metadata.get("total_messages"),
        "input_tokens": metadata.get("input_tokens"),
        "output_tokens": metadata.get("output_tokens"),
        "total_tokens": metadata.get("total_tokens"),
        "runtime_seconds": metadata.get("runtime_seconds"),
        "final_candidate": metadata.get("final_candidate"),
        "decision_method": metadata.get("decision_method"),
        "correct_candidate": metadata.get("correct_candidate"),
        "decision_correct": metadata.get("decision_correct"),
        "mean_pairwise_memory_similarity": metadata.get(
            "mean_pairwise_memory_similarity",
            context.get("mean_pairwise_similarity"),
        ),
        "min_pairwise_memory_similarity": context.get("min_pairwise_similarity"),
        "max_pairwise_memory_similarity": context.get("max_pairwise_similarity"),
        "memory_similarity_method": context.get("method"),
        "embedding_model": context.get("embedding_model"),
        "metadata_file": str(path.relative_to(REPO_ROOT)),
    }

    vote_columns = set()
    for candidate, count in (metadata.get("vote_count") or {}).items():
        column = f"votes_{slug(candidate)}"
        row[column] = count
        vote_columns.add(column)

    similarity_columns = set()
    pairwise = metadata.get("pairwise_memory_similarity") or context.get("pairwise") or []
    for item in pairwise:
        agent_a = slug(item.get("agent_a"))
        agent_b = slug(item.get("agent_b"))
        column = f"similarity_{agent_a}_{agent_b}"
        row[column] = item.get("similarity")
        similarity_columns.add(column)

    return row, vote_columns, similarity_columns


def build_rows(input_root: Path, include_incomplete: bool) -> tuple[list[dict], list[str]]:
    rows = []
    vote_columns = set()
    similarity_columns = set()

    for path in sorted(input_root.glob("**/metadata.json")):
        metadata = read_metadata(path)
        if not include_incomplete and metadata.get("status") != "completed":
            continue

        row, row_vote_columns, row_similarity_columns = flatten_metadata(path, metadata)
        rows.append(row)
        vote_columns.update(row_vote_columns)
        similarity_columns.update(row_similarity_columns)

    for row in rows:
        for column in vote_columns:
            row.setdefault(column, 0)
        for column in similarity_columns:
            row.setdefault(column, "")

    columns = BASE_COLUMNS + sorted(vote_columns) + sorted(similarity_columns)
    rows.sort(
        key=lambda row: (
            CONDITION_ORDER.get(str(row.get("condition")), 99),
            str(row.get("run_id") or ""),
        )
    )
    return rows, columns


def write_csv(output: Path, rows: list[dict], columns: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a flat CSV table from simulation metadata.json files."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include runs whose metadata status is not 'completed'.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows, columns = build_rows(args.input_root, args.include_incomplete)
    write_csv(args.output, rows, columns)
    print(f"Wrote {len(rows)} rows and {len(columns)} columns to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
