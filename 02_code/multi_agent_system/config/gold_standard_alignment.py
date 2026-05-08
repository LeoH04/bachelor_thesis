"""Rule-based gold-standard alignment checks for shared mental models."""

from __future__ import annotations

import re
from typing import Mapping

CHECK_NAMES = (
    "favorite_is_c",
    "c_reliability",
    "c_calmness",
    "c_attention",
    "c_crew_fit",
    "a_risks",
    "b_risks",
    "d_risks",
)


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for deterministic matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _candidate_line_has(text: str, candidate: str, patterns: tuple[str, ...]) -> bool:
    """Return whether a candidate line or local span contains any pattern."""
    candidate_pattern = rf"candidate\s+{candidate.lower()}"
    for raw_line in text.splitlines():
        line = _normalize(raw_line)
        if re.search(candidate_pattern, line) and any(
            re.search(pattern, line) for pattern in patterns
        ):
            return True

    normalized = _normalize(text)
    combined = "|".join(patterns)
    return bool(
        re.search(rf"{candidate_pattern}.{{0,240}}(?:{combined})", normalized)
        or re.search(rf"(?:{combined}).{{0,240}}{candidate_pattern}", normalized)
    )


def _favorite_is_c(text: str) -> bool:
    """Return whether the memory explicitly favors Candidate C."""
    normalized = _normalize(text)
    patterns = (
        r"my current working favorite\s*[-:]?\s*candidate\s+c",
        r"my last vote\s*[-:]?\s*candidate\s+c",
        r"group-leading candidate\s*[-:]?\s*candidate\s+c",
        r"current position\s*[-:]?\s*candidate\s+c",
        r"preferred candidate\s*[-:]?\s*candidate\s+c",
        r"vote\s*[-:]?\s*candidate\s+c",
        r"favor\w*\s+candidate\s+c",
        r"recommend\w*\s+candidate\s+c",
        r"candidate\s+c.{0,120}\b(best|favorite|preferred|leading|choice|recommend)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def score_memory(text: str) -> dict[str, object]:
    """Score one shared mental model against the rule-based gold standard."""
    checks = {
        "favorite_is_c": _favorite_is_c(text),
        "c_reliability": _candidate_line_has(
            text,
            "c",
            (r"100\s*%", r"100\s*percent", r"reliab\w*", r"conscientious"),
        ),
        "c_calmness": _candidate_line_has(
            text,
            "c",
            (r"calm\w*", r"crisis", r"stress"),
        ),
        "c_attention": _candidate_line_has(
            text,
            "c",
            (r"attention", r"attentive", r"concentrat\w*"),
        ),
        "c_crew_fit": _candidate_line_has(
            text,
            "c",
            (
                r"positive atmosphere",
                r"crew",
                r"concern for others",
                r"cooperat\w*",
                r"team\w*",
            ),
        ),
        "a_risks": _candidate_line_has(
            text,
            "a",
            (
                r"criticism",
                r"unorganiz\w*",
                r"show[- ]?off",
                r"not open",
                r"unfriendly",
                r"unhealthy",
            ),
        ),
        "b_risks": _candidate_line_has(
            text,
            "b",
            (
                r"grumpy",
                r"uncooperative",
                r"weak memory",
                r"memory for numbers",
                r"nasty remarks",
                r"pretentious",
                r"wrong tone",
            ),
        ),
        "d_risks": _candidate_line_has(
            text,
            "d",
            (
                r"arrogant",
                r"weak leadership",
                r"know[- ]?it[- ]?all",
                r"hot temper",
                r"moody",
                r"loner",
            ),
        ),
    }
    score = round(sum(checks.values()) / len(CHECK_NAMES), 6)
    return {
        "score": score,
        "checks": {name: int(checks[name]) for name in CHECK_NAMES},
    }


def calculate_gold_standard_alignment(texts: Mapping[str, str]) -> dict[str, object]:
    """Calculate rule-based gold-standard alignment for agent memories."""
    by_agent = []
    for agent_key in sorted(texts):
        text = texts[agent_key]
        if not text.strip():
            continue
        result = score_memory(text)
        by_agent.append(
            {
                "agent": agent_key,
                "score": result["score"],
                "checks": result["checks"],
            }
        )

    values = [float(item["score"]) for item in by_agent]
    return {
        "method": "rule_based_binary_checks",
        "agent_count": len(by_agent),
        "by_agent": by_agent,
        "mean_alignment": round(sum(values) / len(values), 6) if values else None,
        "min_alignment": min(values) if values else None,
        "max_alignment": max(values) if values else None,
    }
