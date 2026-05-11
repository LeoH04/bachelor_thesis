"""Rule-based gold-standard fact coverage checks for shared mental models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .task import AGENT_KEYS, TASK


@dataclass(frozen=True)
class FactSpec:
    """One configured hidden-profile fact with curated matching patterns."""

    fact_id: str
    candidate: str
    text: str
    patterns: tuple[str, ...]


FACT_PATTERNS_BY_TEXT: dict[str, tuple[str, ...]] = {
    "Candidate A can anticipate dangerous situations.": (
        r"anticipat\w*.{0,40}danger\w*",
        r"danger\w*.{0,40}situat\w*",
    ),
    "Candidate A is able to see complex connections.": (
        r"(?:see|sees|understand\w*|recogni[sz]\w*).{0,40}complex.{0,40}connection\w*",
        r"complex.{0,20}connection\w*",
    ),
    "Candidate A has excellent spatial vision.": (
        r"spatial.{0,20}vision",
    ),
    "Candidate A has very good leadership qualities.": (
        r"(?:very\s+good|strong|excellent).{0,40}leadership",
        r"leadership.{0,40}(?:qualities|strong|very\s+good|excellent)",
    ),
    "Candidate B is very conscientious.": (
        r"conscientious",
    ),
    "Candidate B handles stress very well.": (
        r"(?:handle\w*|manage\w*|cope\w*).{0,30}stress.{0,30}(?:very\s+well|well)",
        r"stress.{0,30}(?:very\s+well|well|handling|toleran\w*)",
    ),
    "Candidate B is good at assessing weather conditions.": (
        r"assess\w*.{0,30}weather",
        r"weather.{0,30}(?:assess\w*|conditions?)",
    ),
    "Candidate B has excellent computer skills.": (
        r"excellent.{0,30}computer",
        r"computer.{0,30}skills?",
    ),
    "Candidate C can make correct decisions quickly.": (
        r"correct.{0,30}decisions?.{0,30}quick",
        r"quick.{0,30}correct.{0,30}decisions?",
        r"decisions?.{0,30}quick\w*.{0,30}correct",
    ),
    "Candidate C has difficulty communicating ideas.": (
        r"(?:difficult\w*|trouble|struggl\w*|problems?).{0,40}communicat\w*.{0,30}ideas?",
        r"communicat\w*.{0,30}ideas?.{0,40}(?:difficult|trouble|struggl)",
    ),
    "Candidate C is regarded as egocentric.": (
        r"egocentric",
        r"self[- ]?cent",
    ),
    "Candidate C is not very willing to further his education.": (
        r"not.{0,30}willing.{0,30}(?:further|continu\w*).{0,20}education",
        r"low.{0,30}willingness.{0,30}(?:further|continu\w*).{0,20}education",
        r"unwilling.{0,30}(?:further|continu\w*).{0,20}education",
    ),
    "Candidate D responds to unexpected events adequately.": (
        r"respond\w*.{0,30}unexpected.{0,20}events?.{0,30}adequate",
        r"unexpected.{0,20}events?.{0,30}(?:respond\w*|adequate)",
    ),
    "Candidate D can concentrate very well.": (
        r"concentrat\w*.{0,30}(?:very\s+well|well|excellent)",
        r"very\s+well.{0,30}concentrat",
    ),
    "Candidate D solves problems extremely well.": (
        r"solv\w*.{0,30}problems?.{0,30}(?:extremely\s+well|very\s+well|well)",
        r"problem[- ]?solv\w*.{0,30}(?:extremely|strong|excellent)",
    ),
    "Candidate D takes responsibility seriously.": (
        r"takes?.{0,30}responsibilit\w*.{0,30}serious",
        r"responsibilit\w*.{0,30}serious",
    ),
    "Candidate A is sometimes not good at taking criticism.": (
        r"(?:not|poor|bad|difficulty|trouble).{0,40}(?:tak\w*|accept\w*|receiv\w*).{0,20}criticism",
        r"criticism.{0,40}(?:poorly|badly|not\s+good)",
    ),
    "Candidate A can be unorganized.": (
        r"unorganiz\w*",
        r"disorganiz\w*",
        r"weak.{0,30}organiz\w*",
        r"organiz\w*.{0,30}weak",
    ),
    "Candidate B can be grumpy.": (
        r"grump\w*",
    ),
    "Candidate B can be uncooperative.": (
        r"uncooperat\w*",
        r"not\s+cooperat\w*",
    ),
    "Candidate C is known to be 100% reliable.": (
        r"100\s*%",
        r"100\s*percent",
        r"fully.{0,20}reliab\w*",
        r"complete.{0,20}reliab\w*",
        r"reliab\w*.{0,20}(?:100|fully|complete)",
    ),
    "Candidate C creates a positive atmosphere with his crew.": (
        r"positive.{0,30}atmosphere.{0,30}crew",
        r"crew.{0,30}positive.{0,30}atmosphere",
        r"positive.{0,30}crew.{0,30}atmosphere",
    ),
    "Candidate D is regarded as arrogant.": (
        r"arrogant",
    ),
    "Candidate D has relatively weak leadership skills.": (
        r"weak.{0,30}leadership",
        r"leadership.{0,30}weak",
    ),
    "Candidate A is regarded as a show-off.": (
        r"show[- ]?off",
        r"showbo\w*",
        r"boast\w*",
    ),
    "Candidate A is regarded as being not open to new ideas.": (
        r"not\s+open.{0,30}new\s+ideas",
        r"closed.{0,30}new\s+ideas",
        r"resist\w*.{0,30}new\s+ideas",
    ),
    "Candidate B has a relatively weak memory for numbers.": (
        r"weak.{0,30}memory.{0,30}numbers?",
        r"memory.{0,30}numbers?.{0,30}weak",
        r"numeric.{0,20}memory.{0,30}weak",
        r"weak.{0,30}numeric",
    ),
    "Candidate B makes nasty remarks about his colleagues.": (
        r"nasty.{0,30}remarks?.{0,30}colleagues?",
        r"remarks?.{0,30}colleagues?.{0,30}nasty",
    ),
    "Candidate C keeps calm in a crisis.": (
        r"calm.{0,30}crisis",
        r"crisis.{0,30}calm",
    ),
    "Candidate C understands complicated technology.": (
        r"(?:understand\w*|grasp\w*).{0,40}(?:complicated|complex).{0,30}technolog\w*",
        r"(?:understand\w*|grasp\w*).{0,20}technolog\w*",
    ),
    "Candidate D is regarded as a know-it-all.": (
        r"know[- ]?it[- ]?all",
    ),
    "Candidate D has a hot temper.": (
        r"hot.{0,20}temper",
        r"temper.{0,20}hot",
    ),
    "Candidate A is unfriendly.": (
        r"unfriend\w*",
        r"not\s+friendly",
    ),
    "Candidate A eats unhealthily.": (
        r"eat\w*.{0,30}unhealth\w*",
        r"unhealth\w*.{0,30}(?:eat\w*|habits|diet)",
    ),
    "Candidate B is regarded as pretentious.": (
        r"pretentious",
    ),
    "Candidate B sometimes adopts the wrong tone when communicating.": (
        r"wrong.{0,30}tone",
        r"tone.{0,30}(?:communicat\w*|wrong)",
        r"communicat\w*.{0,30}wrong\s+tone",
    ),
    "Candidate C puts concern for others above everything.": (
        r"concern.{0,30}others",
        r"others.{0,30}above.{0,30}everything",
        r"puts?.{0,30}others.{0,30}(?:first|above)",
        r"care.{0,30}others",
    ),
    "Candidate C has excellent attention skills.": (
        r"excellent.{0,30}attention",
        r"attention.{0,30}skills?",
        r"attentive",
    ),
    "Candidate D is considered moody.": (
        r"moody",
    ),
    "Candidate D is regarded as a loner.": (
        r"loner",
    ),
}

_NORMALIZE_TRANSLATION = str.maketrans(
    {
        0x2010: "-",
        0x2011: "-",
        0x2012: "-",
        0x2013: "-",
        0x2014: "-",
        0x2018: "'",
        0x2019: "'",
    }
)


def _slug(value: object) -> str:
    """Convert text into a stable snake_case identifier fragment."""
    text = str(value or "").replace("%", " percent ")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text or "unknown"


def _normalize(text: str) -> str:
    """Lowercase, normalize punctuation, and collapse whitespace."""
    text = text.translate(_NORMALIZE_TRANSLATION)
    return re.sub(r"\s+", " ", text.lower()).strip()


def _candidate_from_fact(text: str) -> str:
    """Return the candidate letter mentioned by a configured task fact."""
    match = re.match(r"Candidate\s+([A-Z])\b", text)
    if not match:
        raise ValueError(f"Could not derive candidate from fact: {text}")
    return match.group(1).lower()


def _fact_id(source: str, text: str) -> str:
    """Build a stable readable fact identifier from source and fact text."""
    candidate = _candidate_from_fact(text)
    core = re.sub(r"^Candidate\s+[A-Z]\s+", "", text.rstrip("."))
    return f"{source}_candidate_{candidate}_{_slug(core)}"


def _build_fact_specs() -> tuple[FactSpec, ...]:
    """Build fact specs from the configured hidden-profile task."""
    specs = []
    for text in TASK.get("public_information", []):
        fact_text = str(text)
        patterns = FACT_PATTERNS_BY_TEXT[fact_text]
        specs.append(
            FactSpec(
                fact_id=_fact_id("public", fact_text),
                candidate=_candidate_from_fact(fact_text),
                text=fact_text,
                patterns=patterns,
            )
        )

    private_information = TASK.get("private_information", {})
    for agent_key in AGENT_KEYS:
        for text in private_information[agent_key]:
            fact_text = str(text)
            patterns = FACT_PATTERNS_BY_TEXT[fact_text]
            specs.append(
                FactSpec(
                    fact_id=_fact_id(agent_key, fact_text),
                    candidate=_candidate_from_fact(fact_text),
                    text=fact_text,
                    patterns=patterns,
                )
            )
    return tuple(specs)


FACT_SPECS = _build_fact_specs()
CHECK_NAMES = tuple(spec.fact_id for spec in FACT_SPECS)
PRIVATE_FACT_SOURCES = tuple(
    sorted(
        TASK.get("private_information", {}),
        key=lambda source: (-len(source), source),
    )
)
FACT_SOURCE_BUCKETS = ("public", "own_private", "other_private")


def _combined_pattern(patterns: tuple[str, ...]) -> str:
    """Join fact patterns while preserving their local grouping."""
    return "|".join(f"(?:{pattern})" for pattern in patterns)


def _line_mentions_candidate(line: str, candidate: str) -> bool:
    """Return whether a normalized line explicitly references a candidate."""
    candidate_label = rf"candidate\s+{candidate}\b"
    short_label_at_line_start = (
        rf"^\s*(?:[-*]\s*)?(?:\|\s*)?(?:[*_`]+\s*)?"
        rf"{candidate}(?:\s*[*_`]+)?\s*(?:\||[-:])"
    )
    short_label_table_cell = (
        rf"(?:^|\|)\s*(?:[*_`]+)?{candidate}(?:[*_`]+)?\s*(?:\||$)"
    )
    return bool(
        re.search(candidate_label, line)
        or re.search(short_label_at_line_start, line)
        or re.search(short_label_table_cell, line)
    )


def _candidate_line_has(text: str, candidate: str, patterns: tuple[str, ...]) -> bool:
    """Return whether a candidate line or local span contains a fact pattern."""
    combined = _combined_pattern(patterns)
    for raw_line in text.splitlines():
        line = _normalize(raw_line)
        if _line_mentions_candidate(line, candidate) and re.search(combined, line):
            return True

    normalized = _normalize(text)
    candidate_label = rf"candidate\s+{candidate}\b"
    return bool(
        re.search(rf"{candidate_label}.{{0,260}}(?:{combined})", normalized)
        or re.search(rf"(?:{combined}).{{0,260}}{candidate_label}", normalized)
    )


def score_memory(text: str) -> dict[str, object]:
    """Score one shared mental model by coverage of configured task facts."""
    checks = {
        spec.fact_id: _candidate_line_has(text, spec.candidate, spec.patterns)
        for spec in FACT_SPECS
    }
    total_facts = len(FACT_SPECS)
    matched_facts = sum(checks.values())
    score = round(matched_facts / total_facts, 6) if total_facts else None
    return {
        "score": score,
        "matched_facts": matched_facts,
        "total_facts": total_facts,
        "checks": {name: int(checks[name]) for name in CHECK_NAMES},
    }


def _fact_bucket_for_memory(fact_id: str, agent_key: str) -> str | None:
    """Classify a fact as public, own private, or other-agent private."""
    if fact_id.startswith("public_"):
        return "public"

    for source in PRIVATE_FACT_SOURCES:
        if fact_id.startswith(f"{source}_"):
            return "own_private" if source == agent_key else "other_private"

    return None


def fact_source_summary(
    agent_key: str,
    checks: Mapping[str, object],
) -> dict[str, object]:
    """Summarize matched fact checks by source relative to one memory owner."""
    matched = {bucket: 0 for bucket in FACT_SOURCE_BUCKETS}
    totals = {bucket: 0 for bucket in FACT_SOURCE_BUCKETS}

    for fact_id in CHECK_NAMES:
        bucket = _fact_bucket_for_memory(fact_id, agent_key)
        if bucket is None:
            continue

        totals[bucket] += 1
        if int(checks.get(fact_id) or 0):
            matched[bucket] += 1

    summary: dict[str, object] = {}
    for bucket in FACT_SOURCE_BUCKETS:
        total = totals[bucket]
        count = matched[bucket]
        summary[f"matched_{bucket}_facts"] = count
        summary[f"total_{bucket}_facts"] = total
        summary[f"{bucket}_fact_coverage"] = (
            round(count / total, 6) if total else None
        )

    return summary


def summarize_fact_sources(by_agent: list[Mapping[str, object]]) -> dict[str, object]:
    """Return run-level mean fact-source metrics from per-agent alignment rows."""
    summary: dict[str, object] = {}
    for bucket in FACT_SOURCE_BUCKETS:
        matched_values = []
        coverage_values = []
        for item in by_agent:
            matched = item.get(f"matched_{bucket}_facts")
            coverage = item.get(f"{bucket}_fact_coverage")
            if matched is not None:
                matched_values.append(float(matched))
            if coverage is not None:
                coverage_values.append(float(coverage))

        summary[f"mean_{bucket}_facts"] = (
            round(sum(matched_values) / len(matched_values), 6)
            if matched_values
            else None
        )
        summary[f"mean_{bucket}_fact_coverage"] = (
            round(sum(coverage_values) / len(coverage_values), 6)
            if coverage_values
            else None
        )

    return summary


def calculate_gold_standard_alignment(texts: Mapping[str, str]) -> dict[str, object]:
    """Calculate rule-based fact coverage for agent memories."""
    by_agent = []
    for agent_key in sorted(texts):
        result = score_memory(texts[agent_key])
        checks = result["checks"]
        by_agent.append(
            {
                "agent": agent_key,
                "score": result["score"],
                "matched_facts": result["matched_facts"],
                "total_facts": result["total_facts"],
                **fact_source_summary(agent_key, checks),
                "checks": checks,
            }
        )

    values = [
        float(item["score"])
        for item in by_agent
        if item.get("score") is not None
    ]
    return {
        "method": "rule_based_fact_coverage",
        "agent_count": len(by_agent),
        "fact_count": len(FACT_SPECS),
        "by_agent": by_agent,
        "mean_alignment": round(sum(values) / len(values), 6) if values else None,
        "min_alignment": min(values) if values else None,
        "max_alignment": max(values) if values else None,
        **summarize_fact_sources(by_agent),
    }
