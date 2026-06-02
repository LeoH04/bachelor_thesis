#!/usr/bin/env python3
"""Calculate SMM similarity, evidence share, and quality metrics."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import sys
from itertools import combinations
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"
DEFAULT_ENV_FILE = REPO_ROOT / "02_code" / "multi_agent_system" / ".env"
EMBEDDING_TEXT_NORMALIZATION = "collapse_adjacent_duplicate_lines"
_DEFAULT_ENV_LOADED = False

SMM_QUALITY_METHOD = "c_decisive_evidence_coverage_x_memory_similarity"
C_DECISIVE_EVIDENCE_PATTERNS = [
    r"100\s*%\s*reliable|100 percent reliable|100.*reliable",
    r"positive atmosphere|crew atmosphere|positive.*crew",
    (
        r"calm in a crisis|stays calm|keeps calm|calm under pressure|"
        r"calmness under pressure"
    ),
    r"understands complicated technology|complicated technology",
    r"concern for others|others above everything|puts concern",
    r"excellent attention|attention skills|attention",
]

LEGACY_SMM_QUALITY_FIELDS = (
    "c_decisive_evidence_coverage",
    "c_decisive_evidence_consensus",
    "c_decisive_evidence_agent_coverage",
    "c_decisive_evidence_matched_facts",
    "c_decisive_evidence_total_facts",
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


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse one simple dotenv assignment."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].strip()
    if "=" not in line:
        return None

    key, raw_value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None

    try:
        parts = shlex.split(raw_value, comments=True, posix=True)
    except ValueError:
        return key, raw_value.strip().strip("'\"")

    return key, " ".join(parts)


def load_env_file(path: Path) -> None:
    """Load missing environment values from a dotenv-style file."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def load_default_env_files() -> None:
    """Load the repo-local model env file once."""
    global _DEFAULT_ENV_LOADED
    if _DEFAULT_ENV_LOADED:
        return

    load_env_file(DEFAULT_ENV_FILE)
    _DEFAULT_ENV_LOADED = True


def read_memory_texts(run_dir: Path) -> dict[str, str]:
    """Read archived agent shared mental models for one run."""
    memory_dir = run_dir / "shared_mental_models"
    memory_texts = {}

    for path in sorted(memory_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            memory_texts[path.stem] = text

    return memory_texts


def _cosine(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for dense vectors."""
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _required_config_value(key: str) -> str:
    """Return a required embedding configuration value."""
    load_default_env_files()
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required embedding configuration: {key}")
    return value


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


def _collapse_adjacent_duplicate_lines(text: str) -> str:
    """Remove exact adjacent line duplication before embedding archived memories."""
    lines = []
    previous_key = None
    for line in text.splitlines():
        key = line.strip()
        if key == previous_key:
            continue
        lines.append(line.rstrip())
        previous_key = key
    normalized = "\n".join(lines).strip()
    return normalized if normalized else text.strip()


def _embedding_texts(texts: Mapping[str, str]) -> tuple[dict[str, str], dict[str, int]]:
    """Return normalized embedding inputs and per-agent removed line counts."""
    normalized = {}
    removed_counts = {}
    for agent_key, text in texts.items():
        normalized_text = _collapse_adjacent_duplicate_lines(text)
        normalized[agent_key] = normalized_text
        removed_counts[agent_key] = text.count("\n") - normalized_text.count("\n")
    return normalized, removed_counts


def _embedding_vectors(texts: Mapping[str, str], model: str) -> dict[str, list[float]]:
    """Build dense semantic embedding vectors."""
    try:
        from litellm import embedding
    except ModuleNotFoundError as exc:
        if exc.name != "litellm":
            raise
        raise RuntimeError(
            "Missing Python package 'litellm'. Activate the ADK environment with "
            "the project requirements installed."
        ) from exc

    agent_keys = sorted(texts)
    response = embedding(**_embedding_kwargs(model, [texts[key] for key in agent_keys]))
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


def _pairwise_similarity(vectors: Mapping[str, list[float]]) -> list[dict[str, object]]:
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
    """Calculate pairwise SMM similarity from archived memories."""
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

    model = _required_config_value("SIMILARITY_EMBEDDING_MODEL")
    embedding_texts, removed_duplicate_lines = _embedding_texts(non_empty_texts)
    vectors = _embedding_vectors(embedding_texts, model)
    return _similarity_summary(
        embedding_texts,
        _pairwise_similarity(vectors),
        method="embedding_cosine",
        embedding_model=model,
        embedding_text_normalization=EMBEDDING_TEXT_NORMALIZATION,
        embedding_raw_characters={
            agent_key: len(text)
            for agent_key, text in sorted(non_empty_texts.items())
        },
        embedding_input_characters={
            agent_key: len(text)
            for agent_key, text in sorted(embedding_texts.items())
        },
        embedding_removed_adjacent_duplicate_lines=removed_duplicate_lines,
    )


def calculate_fact_share(memory_texts: dict[str, str]) -> float | None:
    """Calculate run-level Candidate C decisive evidence coverage."""
    if len(memory_texts) < 3:
        return None

    possible_matches = len(memory_texts) * len(C_DECISIVE_EVIDENCE_PATTERNS)
    matched = sum(
        1
        for text in memory_texts.values()
        for pattern in C_DECISIVE_EVIDENCE_PATTERNS
        if re.search(pattern, text.lower(), re.IGNORECASE)
    )
    return round(matched / possible_matches, 6)


def calculate_smm_quality(fact_share: float, similarity: float) -> float:
    """Combine evidence coverage and memory similarity into SMM quality."""
    return round(fact_share * similarity, 6)


def stored_memory_similarity(metadata: dict) -> float | None:
    """Return stored mean pairwise memory similarity, if available."""
    value = metadata.get("mean_pairwise_memory_similarity")
    if value is None:
        value = (metadata.get("context_consistency") or {}).get(
            "mean_pairwise_similarity"
        )
    return None if value is None else float(value)


def memory_similarity(
    metadata: dict,
    memory_texts: dict[str, str],
    force: bool,
) -> float | None:
    """Return mean pairwise memory similarity, calculating it when missing."""
    stored = stored_memory_similarity(metadata)
    if stored is not None and not force:
        return stored

    similarity = calculate_memory_similarity(memory_texts)
    metadata.update(
        {
            "context_consistency": similarity,
            "memory_similarity_method": similarity.get("method"),
            "embedding_model": similarity.get("embedding_model"),
            "pairwise_memory_similarity": similarity.get("pairwise", []),
            "mean_pairwise_memory_similarity": similarity.get(
                "mean_pairwise_similarity"
            ),
        }
    )
    return stored_memory_similarity(metadata)


def has_smm_quality(metadata: dict) -> bool:
    """Return whether current simple SMM quality metrics already exist."""
    return (
        metadata.get("smm_similarity") is not None
        and metadata.get("smm_evidence_share") is not None
        and metadata.get("smm_quality") is not None
        and metadata.get("smm_quality_method") == SMM_QUALITY_METHOD
        and all(field not in metadata for field in LEGACY_SMM_QUALITY_FIELDS)
    )


def update_metadata(metadata_path: Path, force: bool) -> str:
    """Calculate one run's SMM quality and write it to metadata."""
    metadata = read_json(metadata_path)

    if metadata.get("status") != "completed":
        return "skipped_incomplete"
    if metadata.get("smm_mode") != "treatment":
        return "skipped_baseline"
    if has_smm_quality(metadata) and not force:
        return "skipped_existing"

    memory_texts = read_memory_texts(metadata_path.parent)
    fact_share = calculate_fact_share(memory_texts)
    if fact_share is None:
        return "skipped_no_memory_files"
    similarity = memory_similarity(metadata, memory_texts, force=force)
    if similarity is None:
        return "skipped_no_memory_similarity"
    quality = calculate_smm_quality(fact_share, similarity)

    for field in LEGACY_SMM_QUALITY_FIELDS:
        metadata.pop(field, None)

    metadata.update(
        {
            "smm_similarity": round(similarity, 6),
            "smm_evidence_share": fact_share,
            "smm_quality": quality,
            "smm_quality_method": SMM_QUALITY_METHOD,
        }
    )
    write_json(metadata_path, metadata)
    return "updated"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate SMM quality and write it to metadata.json files."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute metrics even when current SMM quality fields already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count eligible files without writing metadata.",
    )
    return parser.parse_args()


def main() -> int:
    """Calculate SMM quality for all matching metadata files."""
    args = parse_args()
    metadata_paths = sorted(args.input_root.glob("**/metadata.json"))

    counts = {
        "updated": 0,
        "skipped_baseline": 0,
        "skipped_existing": 0,
        "skipped_incomplete": 0,
        "skipped_no_memory_similarity": 0,
        "skipped_no_memory_files": 0,
    }

    if args.dry_run:
        eligible = 0
        for path in metadata_paths:
            metadata = read_json(path)
            if (
                metadata.get("status") == "completed"
                and metadata.get("smm_mode") == "treatment"
                and (args.force or not has_smm_quality(metadata))
            ):
                eligible += 1
        print(f"Eligible metadata files: {eligible} of {len(metadata_paths)}")
        return 0

    for path in metadata_paths:
        action = update_metadata(path, force=args.force)
        counts[action] = counts.get(action, 0) + 1

    summary = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    print(f"Processed SMM quality metrics ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
