#!/usr/bin/env python3
"""Calculate SMM memory similarity for completed simulation runs."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from itertools import combinations
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"


def _cosine(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for dense vectors."""
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def _config_value(key: str) -> str | None:
    """Return exactly one configured value from env."""
    return os.getenv(key)


def _required_config_value(key: str) -> str:
    """Return a required embedding configuration value or fail clearly."""
    value = _config_value(key)
    if not value:
        raise RuntimeError(f"Missing required embedding configuration: {key}")
    return value


def _embedding_model() -> str:
    """Return the configured semantic embedding model."""
    return _required_config_value("SIMILARITY_EMBEDDING_MODEL")


def _embedding_kwargs(model: str, texts: list[str]) -> dict[str, object]:
    """Build LiteLLM embedding kwargs from the dedicated embedding config."""
    return {
        "model": model,
        "input": texts,
        "api_key": _required_config_value("EMBEDDING_API_KEY"),
        "api_base": _required_config_value("EMBEDDING_API_BASE"),
        "encoding_format": "float",
        "input_type": _required_config_value("EMBEDDING_INPUT_TYPE"),
    }


def _coerce_embedding_data(response: object) -> list[object]:
    """Extract the data list from common LiteLLM response shapes."""
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    return list(data or [])


def _coerce_embedding(item: object) -> list[float]:
    """Extract one embedding vector from common LiteLLM response item shapes."""
    embedding = getattr(item, "embedding", None)
    if embedding is None and isinstance(item, dict):
        embedding = item.get("embedding")
    return [float(value) for value in embedding or []]


def _embedding_vectors(texts: Mapping[str, str], model: str) -> dict[str, list[float]]:
    """Build dense semantic embedding vectors with LiteLLM when configured."""
    from litellm import embedding

    agent_keys = sorted(texts)
    kwargs = _embedding_kwargs(model, [texts[key] for key in agent_keys])
    response = embedding(**kwargs)

    data = _coerce_embedding_data(response)
    vectors = {
        agent_key: _coerce_embedding(item)
        for agent_key, item in zip(agent_keys, data)
    }

    if len(vectors) != len(agent_keys) or any(not vector for vector in vectors.values()):
        raise ValueError(
            "Embedding response did not contain one non-empty vector per memory."
        )

    return vectors


def _pairwise_similarity(
    vectors: Mapping[str, list[float]],
) -> list[dict[str, object]]:
    """Calculate all pairwise cosine similarities."""
    pairwise = []
    for left_key, right_key in combinations(sorted(vectors), 2):
        similarity = _cosine(vectors[left_key], vectors[right_key])
        pairwise.append(
            {
                "agent_a": left_key,
                "agent_b": right_key,
                "similarity": round(similarity, 6),
            }
        )
    return pairwise


def _similarity_summary(
    texts: Mapping[str, str],
    pairwise: list[dict[str, object]],
    **extra: object,
) -> dict[str, object]:
    """Return pairwise similarities plus aggregate context-consistency fields."""
    values = [float(item["similarity"]) for item in pairwise]
    summary = {
        "pairwise": pairwise,
        "mean_pairwise_similarity": round(sum(values) / len(values), 6)
        if values
        else None,
        "min_pairwise_similarity": min(values) if values else None,
        "max_pairwise_similarity": max(values) if values else None,
    }
    summary.update(extra)
    return summary


def calculate_memory_similarity(texts: Mapping[str, str]) -> dict[str, object]:
    """Calculate pairwise shared-mental-model similarity for a completed run."""
    non_empty_texts = {
        agent_key: text
        for agent_key, text in texts.items()
        if text.strip()
    }
    if len(non_empty_texts) < 2:
        return _similarity_summary(
            non_empty_texts,
            [],
            reason="not_enough_memories",
        )

    model = _embedding_model()
    vectors = _embedding_vectors(non_empty_texts, model)
    return _similarity_summary(
        non_empty_texts,
        _pairwise_similarity(vectors),
    )


def read_metadata(path: Path) -> dict:
    """Read one metadata.json file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_metadata(path: Path, metadata: dict) -> None:
    """Write one metadata.json file in the repository's standard format."""
    path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def memory_dir_for(metadata_file: Path, metadata: dict) -> Path:
    """Return the shared mental model directory for one run."""
    configured = (metadata.get("paths") or {}).get("shared_mental_models")
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    return metadata_file.parent / "shared_mental_models"


def memory_texts_from(memory_dir: Path) -> tuple[dict[str, str], list[str]]:
    """Read agent memory markdown files from a run directory."""
    memory_texts = {}
    memory_files = []
    for path in sorted(memory_dir.glob("agent_*.md")):
        memory_files.append(str(path))
        memory_texts[path.stem] = path.read_text(encoding="utf-8")
    return memory_texts, memory_files


def metadata_files_from(args: argparse.Namespace) -> list[Path]:
    """Return metadata files selected by CLI arguments."""
    if args.run_dir:
        paths = []
        for run_dir in args.run_dir:
            path = run_dir if run_dir.name == "metadata.json" else run_dir / "metadata.json"
            paths.append(path)
        return paths
    return sorted(args.input_root.glob("**/metadata.json"))


def should_skip(metadata: dict, force: bool, include_incomplete: bool) -> str | None:
    """Return a skip reason, or None when the run should be processed."""
    if not include_incomplete and metadata.get("status") != "completed":
        return "incomplete"
    if metadata.get("smm_mode") == "baseline":
        return "baseline"
    if (
        metadata.get("mean_pairwise_memory_similarity") is not None
        or metadata.get("pairwise_memory_similarity")
    ) and not force:
        return "already_calculated"
    return None


def update_similarity(metadata_file: Path, force: bool, include_incomplete: bool) -> str:
    """Calculate and persist memory similarity for one run."""
    if not metadata_file.exists():
        return "missing_metadata"

    metadata = read_metadata(metadata_file)
    skip_reason = should_skip(metadata, force, include_incomplete)
    if skip_reason:
        return skip_reason

    memory_dir = memory_dir_for(metadata_file, metadata)
    if not memory_dir.exists():
        return "missing_memory_dir"

    memory_texts, memory_files = memory_texts_from(memory_dir)
    similarity = calculate_memory_similarity(memory_texts)

    metadata.update(
        {
            "shared_mental_models_archived": True,
            "shared_mental_model_files": memory_files,
            "context_consistency": similarity,
            "pairwise_memory_similarity": similarity.get("pairwise", []),
            "mean_pairwise_memory_similarity": similarity.get(
                "mean_pairwise_similarity"
            ),
        }
    )
    write_metadata(metadata_file, metadata)
    return "updated"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate semantic similarity for saved SMM memory files."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument(
        "--run-dir",
        action="append",
        type=Path,
        help="Specific run directory or metadata.json file to process.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalculate runs that already have embedding similarity.",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include runs whose metadata status is not 'completed'.",
    )
    return parser.parse_args()


def main() -> int:
    """Calculate memory similarity for selected runs."""
    args = parse_args()
    counts: dict[str, int] = {}

    for metadata_file in metadata_files_from(args):
        status = update_similarity(
            metadata_file,
            force=args.force,
            include_incomplete=args.include_incomplete,
        )
        counts[status] = counts.get(status, 0) + 1

    total = sum(counts.values())
    summary = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    print(f"Processed {total} metadata files ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
