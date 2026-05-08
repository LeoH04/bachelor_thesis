#!/usr/bin/env python3
"""Backfill gold-standard shared-mental-model metrics into existing metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "02_code" / "multi_agent_system"
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"
DEFAULT_GOLD_STANDARD = (
    REPO_ROOT
    / "01_data"
    / "gold_standard"
    / "gold_standard_shared_mental_model.md"
)

sys.path.insert(0, str(PACKAGE_ROOT))
from config.similarity import calculate_gold_standard_similarity  # noqa: E402


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
    mean_gold_standard_similarity: object,
) -> float | None:
    """Return the product of pairwise and gold-standard mean similarity."""
    if mean_pairwise_similarity is None or mean_gold_standard_similarity is None:
        return None
    return round(
        float(mean_pairwise_similarity) * float(mean_gold_standard_similarity),
        6,
    )


def mean_pairwise_similarity(metadata: dict) -> object:
    """Return the stored mean pairwise similarity from old or current metadata."""
    context = metadata.get("context_consistency") or {}
    return metadata.get(
        "mean_pairwise_memory_similarity",
        context.get("mean_pairwise_similarity"),
    )


def has_gold_metrics(metadata: dict) -> bool:
    """Return whether the new gold-standard metrics are already present."""
    return (
        "gold_standard_memory_similarity" in metadata
        and "mean_gold_standard_memory_similarity" in metadata
        and "context_alignment" in metadata
    )


def backfill_metadata(
    metadata_path: Path,
    gold_standard_text: str,
    gold_standard_path: Path,
    force: bool,
) -> str:
    """Backfill one metadata file and return an action label."""
    metadata = read_json(metadata_path)
    if metadata.get("status") != "completed":
        return "skipped_incomplete"
    if not metadata.get("shared_mental_models_archived"):
        return "skipped_no_memories"
    if has_gold_metrics(metadata) and not force:
        return "skipped_existing"

    memory_texts = read_memory_texts(metadata_path.parent)
    if not memory_texts:
        return "skipped_no_memory_files"

    similarity = calculate_gold_standard_similarity(
        memory_texts,
        gold_standard_text,
    )
    mean_gold = similarity.get("mean_similarity")

    metadata.pop("gold_standard_similarity", None)
    metadata.update(
        {
            "gold_standard_memory_similarity": similarity.get("by_agent", []),
            "mean_gold_standard_memory_similarity": mean_gold,
            "min_gold_standard_memory_similarity": similarity.get("min_similarity"),
            "max_gold_standard_memory_similarity": similarity.get("max_similarity"),
            "context_alignment": context_alignment_score(
                mean_pairwise_similarity(metadata),
                mean_gold,
            ),
            "gold_standard_similarity_method": similarity.get("method"),
            "gold_standard_file": str(gold_standard_path),
        }
    )
    write_json(metadata_path, metadata)
    return "updated"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Backfill gold-standard SMM similarity and context alignment into "
            "existing simulation metadata.json files."
        )
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--gold-standard", type=Path, default=DEFAULT_GOLD_STANDARD)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute metrics even when gold-standard fields already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count eligible files without calling the embedding API or writing metadata.",
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
                and (args.force or not has_gold_metrics(metadata))
            ):
                eligible += 1
        print(f"Eligible metadata files: {eligible} of {len(metadata_paths)}")
        return 0

    if not args.gold_standard.exists():
        raise FileNotFoundError(f"Gold standard not found: {args.gold_standard}")

    gold_standard_text = args.gold_standard.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    for path in metadata_paths:
        action = backfill_metadata(
            path,
            gold_standard_text,
            args.gold_standard,
            args.force,
        )
        counts[action] = counts.get(action, 0) + 1

    print("Backfill complete:")
    for action, count in sorted(counts.items()):
        print(f"- {action}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
