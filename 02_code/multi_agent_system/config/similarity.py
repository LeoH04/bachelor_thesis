"""Pairwise similarity metrics for archived shared mental models."""

from __future__ import annotations

import math
import os
from itertools import combinations
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = (REPO_ROOT / ".env", PACKAGE_ROOT / ".env")


def _cosine(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for dense vectors."""
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def _read_env_file_value(path: Path, key: str) -> str | None:
    """Read one key from a simple .env file without mutating process env."""
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()

        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            return value.strip().strip("\"'")

    return None


def _config_value(key: str) -> str | None:
    """Return exactly one configured value from env or the project .env files."""
    value = os.getenv(key)
    if value:
        return value

    for env_file in ENV_FILES:
        value = _read_env_file_value(env_file, key)
        if value:
            return value

    return None


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
    kwargs: dict[str, object] = {
        "model": model,
        "input": texts,
        "api_key": _required_config_value("EMBEDDING_API_KEY"),
        "api_base": _required_config_value("EMBEDDING_API_BASE"),
        "encoding_format": "float",
        "input_type": _required_config_value("EMBEDDING_INPUT_TYPE"),
    }

    return kwargs


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
    response = embedding(**_embedding_kwargs(model, [texts[key] for key in agent_keys]))
    data = _coerce_embedding_data(response)
    vectors = {
        agent_key: _coerce_embedding(item)
        for agent_key, item in zip(agent_keys, data)
    }

    if len(vectors) != len(agent_keys) or any(not vector for vector in vectors.values()):
        raise ValueError("Embedding response did not contain one non-empty vector per memory.")

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
    method: str,
    texts: Mapping[str, str],
    pairwise: list[dict[str, object]],
    **extra: object,
) -> dict[str, object]:
    """Return pairwise similarities plus aggregate context-consistency fields."""
    values = [float(item["similarity"]) for item in pairwise]
    summary = {
        "method": method,
        "agent_count": len(texts),
        "pairwise": pairwise,
        "mean_pairwise_similarity": round(sum(values) / len(values), 6) if values else None,
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
        return _similarity_summary("not_enough_memories", non_empty_texts, [])

    model = _embedding_model()
    vectors = _embedding_vectors(non_empty_texts, model)
    return _similarity_summary(
        "embedding_cosine",
        non_empty_texts,
        _pairwise_similarity(vectors),
        embedding_model=model,
    )
