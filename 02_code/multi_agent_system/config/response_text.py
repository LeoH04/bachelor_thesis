"""Parse and normalize model response text."""

import json
import re
from typing import Iterable

from .task import TASK

PUBLIC_MESSAGE_LABEL = "PUBLIC_MESSAGE"
METADATA_JSON_LABEL = "METADATA_JSON"
MEMORY_MARKDOWN_LABEL = "MEMORY_MARKDOWN"
PUBLIC_MESSAGE_PREFIX_RE = re.compile(
    rf"^\s*{PUBLIC_MESSAGE_LABEL}\s*:\s*",
    re.IGNORECASE,
)
PUBLIC_MESSAGE_SECTION_RE = re.compile(
    rf"(?:^|\n)\s*{PUBLIC_MESSAGE_LABEL}\s*:\s*(.*)",
    re.DOTALL | re.IGNORECASE,
)
METADATA_JSON_LABEL_RE = re.compile(
    rf"\b{METADATA_JSON_LABEL}\s*:",
    re.IGNORECASE,
)
METADATA_JSON_BLOCK_RE = re.compile(
    rf"\b{METADATA_JSON_LABEL}\s*:\s*(\{{.*?\}})",
    re.DOTALL | re.IGNORECASE,
)
MEMORY_MARKDOWN_PREFIX_RE = re.compile(
    rf"^\s*{MEMORY_MARKDOWN_LABEL}\s*:\s*",
    re.IGNORECASE,
)


def _clean_public_message(text: str) -> str:
    """Strip wrapper labels and tool traces from text before storing it publicly."""
    text = PUBLIC_MESSAGE_PREFIX_RE.sub("", text)

    visible_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "For context:":
            continue
        if "called tool `" in stripped or "tool returned result:" in stripped:
            continue
        visible_lines.append(line.rstrip())

    return "\n".join(visible_lines).strip()


def _extract_public_message(text: str) -> str:
    """Extract the public answer from a scheduled agent response."""
    match = PUBLIC_MESSAGE_SECTION_RE.search(text)
    if match:
        return _clean_public_message(match.group(1))

    return ""


def extract_vote_from_response(text: object) -> str | None:
    """Extract a valid vote from a scheduled agent response stored in state."""
    if not isinstance(text, str):
        return None

    match = METADATA_JSON_BLOCK_RE.search(text)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    vote = data.get("vote")
    return str(vote) if vote in TASK.get("candidates", []) else None


def _is_thought_part(part: object) -> bool:
    """Return whether a model response part is internal reasoning."""
    return bool(getattr(part, "thought", False))


def _visible_text_from_parts(parts: Iterable[object]) -> str:
    """Join only non-thought text parts from an ADK model response."""
    return "\n".join(
        part.text
        for part in parts
        if getattr(part, "text", None) and not _is_thought_part(part)
    ).strip()


def _drop_thought_parts(parts: list[object]) -> list[object]:
    """Return non-thought parts without mutating the ADK response content."""
    return [part for part in parts if not _is_thought_part(part)]


def _dict_part_text(part: dict) -> str:
    """Return visible text from a serialized response part."""
    if part.get("thought"):
        return ""

    return str(part.get("text", "")).strip()


def _serialized_parts_text(parts: object) -> str:
    """Join visible text from serialized response parts."""
    if not isinstance(parts, list):
        return ""

    return "\n".join(
        text
        for text in (_dict_part_text(part) for part in parts if isinstance(part, dict))
        if text
    ).strip()


def _replace_response_text(llm_response, text: str) -> None:
    """Replace visible response text while preserving thought parts when possible."""
    content = getattr(llm_response, "content", None)
    if content is None:
        return

    parts = list(getattr(content, "parts", None) or [])

    try:
        from google.genai import types

        replacement_part = types.Part.from_text(text=text)
        if not parts:
            content.parts = [replacement_part]
            return

        new_parts = []
        inserted_replacement = False
        for part in parts:
            if _is_thought_part(part):
                new_parts.append(part)
            elif not inserted_replacement:
                new_parts.append(replacement_part)
                inserted_replacement = True

        if not inserted_replacement:
            new_parts.append(replacement_part)

        content.parts = new_parts
        return
    except Exception:
        pass

    try:
        new_parts = []
        inserted_replacement = False
        for part in parts:
            if _is_thought_part(part):
                new_parts.append(part)
            elif not inserted_replacement:
                part.text = text
                new_parts.append(part)
                inserted_replacement = True

        if inserted_replacement:
            content.parts = new_parts
    except Exception:
        pass


def _public_value_text(value: object) -> str:
    """Render a tool argument or result as concise public discussion text."""
    content = getattr(value, "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    parts = parts or getattr(value, "parts", None)
    if parts:
        return _clean_public_message(_visible_text_from_parts(parts))

    if isinstance(value, dict):
        content_value = value.get("content")
        if isinstance(content_value, dict):
            content_text = _serialized_parts_text(content_value.get("parts"))
            if content_text:
                return _clean_public_message(content_text)

        parts_text = _serialized_parts_text(value.get("parts"))
        if parts_text:
            return _clean_public_message(parts_text)

        parts = []
        for key, item in value.items():
            item_text = _clean_public_message(str(item))
            if item_text:
                parts.append(f"{key}: {item_text}")
        return "; ".join(parts).strip()

    return _clean_public_message(str(value)).strip()
