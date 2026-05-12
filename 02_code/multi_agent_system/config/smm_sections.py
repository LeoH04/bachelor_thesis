"""Shared Mental Model markdown section helpers."""

from __future__ import annotations

import re
from typing import Mapping


SECTION_ORDER = (
    "task_summary",
    "revealed_facts_by_source",
    "candidate_evaluation",
    "my_position",
    "other_agents_positions",
    "emerging_group_view",
    "open_questions_next_step_focus",
)

SECTION_TITLES = {
    "task_summary": "Task Summary",
    "revealed_facts_by_source": "Revealed Facts by Source",
    "candidate_evaluation": "Candidate Evaluation",
    "my_position": "My Position",
    "other_agents_positions": "Other Agents' Positions",
    "emerging_group_view": "Emerging Group View",
    "open_questions_next_step_focus": "Open Questions and Next-Step Focus",
}

SECTION_WEIGHTS = {
    "task_summary": 0.02,
    "revealed_facts_by_source": 0.30,
    "candidate_evaluation": 0.35,
    "my_position": 0.00,
    "other_agents_positions": 0.15,
    "emerging_group_view": 0.13,
    "open_questions_next_step_focus": 0.05,
}

_SECTION_MARKER_RE = re.compile(
    r"<!--\s*SMM_SECTION:(?P<section>[a-z_]+):start\s*-->\s*"
    r"(?P<body>.*?)"
    r"\s*<!--\s*SMM_SECTION:(?P=section):end\s*-->",
    re.DOTALL | re.IGNORECASE,
)
_LEADING_HEADING_RE = re.compile(r"^\s*#{1,6}\s+.+?(?:\n+|$)")
_SMM_MARKER_RE = re.compile(r"<!--\s*SMM_SECTION:[^>]+-->\s*", re.IGNORECASE)


def section_start_marker(section_id: str) -> str:
    """Return the start marker for a canonical memory section."""
    return f"<!-- SMM_SECTION:{section_id}:start -->"


def section_end_marker(section_id: str) -> str:
    """Return the end marker for a canonical memory section."""
    return f"<!-- SMM_SECTION:{section_id}:end -->"


def clean_section_body(body: str) -> str:
    """Remove nested section markers and accidental leading headings from a body."""
    cleaned = _SMM_MARKER_RE.sub("", body).strip()
    return _LEADING_HEADING_RE.sub("", cleaned, count=1).strip()


def parse_marked_sections(markdown: str) -> dict[str, str]:
    """Extract canonical memory sections by machine-readable markers."""
    sections = {}
    for match in _SECTION_MARKER_RE.finditer(markdown):
        section_id = match.group("section").lower()
        if section_id in SECTION_ORDER and section_id not in sections:
            sections[section_id] = clean_section_body(match.group("body"))
    return sections


def render_marked_memory(title: str, sections: Mapping[str, str]) -> str:
    """Render a full Shared Mental Model markdown document with stable sections."""
    blocks = [title.strip()]
    for section_id in SECTION_ORDER:
        section_title = SECTION_TITLES[section_id]
        body = clean_section_body(sections.get(section_id, ""))
        blocks.append(
            "\n".join(
                (
                    f"## {section_title}",
                    section_start_marker(section_id),
                    body,
                    section_end_marker(section_id),
                )
            )
        )
    return "\n\n".join(blocks).strip()
