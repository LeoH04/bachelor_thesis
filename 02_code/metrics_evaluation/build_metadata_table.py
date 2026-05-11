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
PACKAGE_ROOT = REPO_ROOT / "02_code" / "multi_agent_system"
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"
DEFAULT_OUTPUT = REPO_ROOT / "01_data" / "processed" / "simulation_metrics.csv"

sys.path.insert(0, str(PACKAGE_ROOT))
from config.gold_standard_alignment import (  # noqa: E402
    FACT_SOURCE_BUCKETS,
    fact_source_summary,
    summarize_fact_sources,
)

BASE_COLUMNS = [
    "run_id",
    "condition",
    "smm_mode",
    "explicit_smm_memory",
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
    "mean_gold_standard_alignment",
    "min_gold_standard_alignment",
    "max_gold_standard_alignment",
    "mean_public_facts",
    "mean_public_fact_coverage",
    "mean_own_private_facts",
    "mean_own_private_fact_coverage",
    "mean_other_private_facts",
    "mean_other_private_fact_coverage",
    "context_alignment",
    "memory_similarity_method",
    "gold_standard_alignment_method",
    "embedding_model",
    "metadata_file",
]

CONDITION_ORDER = {"low": 0, "moderate": 1, "high": 2}
SMM_MODE_ORDER = {"baseline": 0, "treatment": 1}


def slug(value: object) -> str:
    """Convert labels like 'Candidate A' into stable CSV column parts."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def read_metadata(path: Path) -> dict:
    """Read and parse one metadata.json file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def product_or_none(left: object, right: object) -> float | None:
    """Return a rounded product when both values are present."""
    if left is None or right is None or left == "" or right == "":
        return None
    return round(float(left) * float(right), 6)


def gold_alignment_rows_with_fact_sources(metadata: dict) -> list[dict]:
    """Return per-agent gold rows, deriving fact-source fields if needed."""
    rows = []
    for item in metadata.get("gold_standard_alignment") or []:
        row = dict(item)
        checks = row.get("checks") or {}
        agent = str(row.get("agent") or "")
        if checks and "matched_other_private_facts" not in row:
            row.update(fact_source_summary(agent, checks))
        rows.append(row)
    return rows


def flatten_metadata(path: Path, metadata: dict) -> tuple[dict, set[str], set[str]]:
    """Convert nested run metadata into one flat CSV row."""
    context = metadata.get("context_consistency") or {}
    gold_alignment_rows = gold_alignment_rows_with_fact_sources(metadata)
    source_summary = summarize_fact_sources(gold_alignment_rows)
    mean_pairwise = metadata.get(
        "mean_pairwise_memory_similarity",
        context.get("mean_pairwise_similarity"),
    )
    mean_gold_alignment = metadata.get("mean_gold_standard_alignment")
    row = {
        "run_id": metadata.get("run_id"),
        "condition": metadata.get("condition"),
        "smm_mode": metadata.get("smm_mode", "treatment"),
        "explicit_smm_memory": metadata.get("explicit_smm_memory", True),
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
        "mean_pairwise_memory_similarity": mean_pairwise,
        "min_pairwise_memory_similarity": context.get("min_pairwise_similarity"),
        "max_pairwise_memory_similarity": context.get("max_pairwise_similarity"),
        "mean_gold_standard_alignment": mean_gold_alignment,
        "min_gold_standard_alignment": metadata.get("min_gold_standard_alignment"),
        "max_gold_standard_alignment": metadata.get("max_gold_standard_alignment"),
        **{
            f"mean_{bucket}_facts": metadata.get(
                f"mean_{bucket}_facts",
                source_summary.get(f"mean_{bucket}_facts"),
            )
            for bucket in FACT_SOURCE_BUCKETS
        },
        **{
            f"mean_{bucket}_fact_coverage": metadata.get(
                f"mean_{bucket}_fact_coverage",
                source_summary.get(f"mean_{bucket}_fact_coverage"),
            )
            for bucket in FACT_SOURCE_BUCKETS
        },
        "context_alignment": metadata.get(
            "context_alignment",
            product_or_none(mean_pairwise, mean_gold_alignment),
        ),
        "memory_similarity_method": context.get("method"),
        "gold_standard_alignment_method": metadata.get(
            "gold_standard_alignment_method"
        ),
        "embedding_model": context.get("embedding_model"),
        "metadata_file": str(path.resolve().relative_to(REPO_ROOT)),
    }

    vote_columns = set()
    for candidate, count in (metadata.get("vote_count") or {}).items():
        column = f"votes_{slug(candidate)}"
        row[column] = count
        vote_columns.add(column)

    context_consistency_columns = set()
    pairwise = metadata.get("pairwise_memory_similarity") or context.get("pairwise") or []
    for item in pairwise:
        agent_a = slug(item.get("agent_a"))
        agent_b = slug(item.get("agent_b"))
        column = f"similarity_{agent_a}_{agent_b}"
        row[column] = item.get("similarity")
        context_consistency_columns.add(column)

    for item in gold_alignment_rows:
        agent = slug(item.get("agent"))
        column = f"gold_alignment_{agent}"
        row[column] = item.get("score")
        context_consistency_columns.add(column)
        for check, value in (item.get("checks") or {}).items():
            check_column = f"gold_check_{agent}_{slug(check)}"
            row[check_column] = value
            context_consistency_columns.add(check_column)

    return row, vote_columns, context_consistency_columns


def build_rows(input_root: Path, include_incomplete: bool) -> tuple[list[dict], list[str]]:
    """Collect metadata rows and derive the final CSV column order."""
    rows = []
    vote_columns = set()
    context_consistency_columns = set()

    for path in sorted(input_root.glob("**/metadata.json")):
        metadata = read_metadata(path)
        if not include_incomplete and metadata.get("status") != "completed":
            continue

        row, row_vote_columns, row_context_consistency_columns = flatten_metadata(path, metadata)
        rows.append(row)
        vote_columns.update(row_vote_columns)
        context_consistency_columns.update(row_context_consistency_columns)

    for row in rows:
        for column in vote_columns:
            row.setdefault(column, 0)
        for column in context_consistency_columns:
            row.setdefault(column, "")

    columns = BASE_COLUMNS + sorted(vote_columns) + sorted(context_consistency_columns)
    rows.sort(
        key=lambda row: (
            CONDITION_ORDER.get(str(row.get("condition")), 99),
            SMM_MODE_ORDER.get(str(row.get("smm_mode")), 99),
            str(row.get("run_id") or ""),
        )
    )
    return rows, columns


def infer_output_id(rows: list[dict]) -> str | None:
    """Infer the run or batch id to include in the default output filename."""
    run_ids = {str(row.get("run_id") or "") for row in rows if row.get("run_id")}
    if len(run_ids) == 1:
        return next(iter(run_ids))

    batch_ids = set()
    for run_id in run_ids:
        match = re.fullmatch(
            r"(?:low|moderate|high)_(?:baseline|treatment)_(.+)_\d+",
            run_id,
        )
        if not match:
            match = re.fullmatch(r"(?:low|moderate|high)_(.+)_\d+", run_id)
        if not match:
            return None
        batch_ids.add(match.group(1))

    if len(batch_ids) == 1:
        return next(iter(batch_ids))
    return None


def write_csv(output: Path, rows: list[dict], columns: list[str]) -> None:
    """Write rows to a CSV file, creating the output directory if needed."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the metadata table builder."""
    parser = argparse.ArgumentParser(
        description="Build a flat CSV table from simulation metadata.json files."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include runs whose metadata status is not 'completed'.",
    )
    return parser.parse_args()


def main() -> int:
    """Build the metadata CSV and return a process exit code."""
    args = parse_args()
    rows, columns = build_rows(args.input_root, args.include_incomplete)
    output = args.output
    if output is None:
        output_id = infer_output_id(rows)
        output = (
            DEFAULT_OUTPUT.with_name(f"simulation_metrics_{output_id}.csv")
            if output_id
            else DEFAULT_OUTPUT
        )

    write_csv(output, rows, columns)
    print(f"Wrote {len(rows)} rows and {len(columns)} columns to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
