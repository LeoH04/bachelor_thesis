#!/usr/bin/env python3
"""Backfill rule-based gold-standard fact coverage into existing metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "02_code" / "multi_agent_system"
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"

sys.path.insert(0, str(PACKAGE_ROOT))
from config.gold_standard_alignment import calculate_gold_standard_alignment  # noqa: E402


OLD_GOLD_STANDARD_FIELDS = (
    "gold_standard_similarity",
    "gold_standard_memory_similarity",
    "mean_gold_standard_memory_similarity",
    "min_gold_standard_memory_similarity",
    "max_gold_standard_memory_similarity",
    "gold_standard_similarity_method",
    "gold_standard_file",
)


def read_json(path: Path) -> dict:
    """Read one metadata file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    """Write one metadata file in the project's deterministic style."""
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_memory_texts(run_dir: Path) -> dict[str, str]:
    """Read archived agent shared mental models for one run."""
    memory_texts = {}
    for path in sorted((run_dir / "shared_mental_models").glob("agent_*.md")):
        text = path.read_text(encoding="utf-8")
        if text.strip():
            memory_texts[path.stem] = text
    return memory_texts


def context_alignment_score(
    mean_pairwise_similarity: object,
    mean_gold_standard_alignment: object,
) -> float | None:
    """Return the product of pairwise similarity and gold-standard alignment."""
    if mean_pairwise_similarity is None or mean_gold_standard_alignment is None:
        return None
    return round(
        float(mean_pairwise_similarity) * float(mean_gold_standard_alignment),
        6,
    )


def mean_pairwise_similarity(metadata: dict) -> object:
    """Return the stored mean pairwise similarity from old or current metadata."""
    context = metadata.get("context_consistency") or {}
    return metadata.get(
        "mean_pairwise_memory_similarity",
        context.get("mean_pairwise_similarity"),
    )


def has_gold_alignment(metadata: dict) -> bool:
    """Return whether current rule-based fact coverage is already present."""
    return (
        "gold_standard_alignment" in metadata
        and "mean_gold_standard_alignment" in metadata
        and "context_alignment" in metadata
        and metadata.get("gold_standard_alignment_method")
        == "rule_based_fact_coverage"
    )


def remove_old_gold_standard_fields(metadata: dict) -> None:
    """Remove embedding-based gold-standard fields from metadata."""
    for field in OLD_GOLD_STANDARD_FIELDS:
        metadata.pop(field, None)


def backfill_metadata(metadata_path: Path, force: bool) -> str:
    """Backfill one metadata file and return an action label."""
    metadata = read_json(metadata_path)
    if metadata.get("status") != "completed":
        return "skipped_incomplete"
    if not metadata.get("shared_mental_models_archived"):
        return "skipped_no_memories"
    if has_gold_alignment(metadata) and not force:
        return "skipped_existing"

    memory_texts = read_memory_texts(metadata_path.parent)
    if not memory_texts:
        return "skipped_no_memory_files"

    alignment = calculate_gold_standard_alignment(memory_texts)
    mean_alignment = alignment.get("mean_alignment")

    remove_old_gold_standard_fields(metadata)
    metadata.update(
        {
            "gold_standard_alignment": alignment.get("by_agent", []),
            "mean_gold_standard_alignment": mean_alignment,
            "min_gold_standard_alignment": alignment.get("min_alignment"),
            "max_gold_standard_alignment": alignment.get("max_alignment"),
            "context_alignment": context_alignment_score(
                mean_pairwise_similarity(metadata),
                mean_alignment,
            ),
            "gold_standard_alignment_method": alignment.get("method"),
        }
    )
    write_json(metadata_path, metadata)
    return "updated"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Backfill rule-based gold-standard fact coverage and context alignment "
            "into existing simulation metadata.json files."
        )
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute metrics even when gold-standard alignment already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count eligible files without writing metadata.",
    )
    return parser.parse_args()


def main() -> int:
    """Backfill all matching metadata files."""
    args = parse_args()
    metadata_paths = sorted(args.input_root.glob("**/metadata.json"))

    if args.dry_run:
        eligible = 0
        for path in metadata_paths:
            metadata = read_json(path)
            if (
                metadata.get("status") == "completed"
                and metadata.get("shared_mental_models_archived")
                and (args.force or not has_gold_alignment(metadata))
            ):
                eligible += 1
        print(f"Eligible metadata files: {eligible} of {len(metadata_paths)}")
        return 0

    counts: dict[str, int] = {}
    for path in metadata_paths:
        action = backfill_metadata(path, args.force)
        counts[action] = counts.get(action, 0) + 1

    print("Backfill complete:")
    for action, count in sorted(counts.items()):
        print(f"- {action}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
