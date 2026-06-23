#!/usr/bin/env python3
"""Calculate transcript-based team-process metrics for simulation runs.

The measure follows Mathieu et al.'s three team-process components:
communication, coordination, and cooperation. Each dimension is represented by
one transcript-based indicator:

- communication: decisive Candidate C evidence uptake
- coordination: inquiry network coverage
- cooperation: response integration

The calculation uses only public transcript behavior, not correctness, runtime,
token counts, or SMM memory files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "final" / "final_100_gpt_oss_120b"

AGENT_LABELS = ("agent_1", "agent_2", "agent_3")

DECISIVE_C_FACTS: list[dict[str, Any]] = [
    {
        "id": "c_100_percent_reliable",
        "patterns": [r"100\s*(?:%|percent) reliable", r"completely reliable"],
    },
    {
        "id": "c_positive_crew_atmosphere",
        "patterns": [r"positive (?:crew )?atmosphere", r"atmosphere with (?:his|the) crew"],
    },
    {
        "id": "c_calm_in_crisis",
        "patterns": [
            r"calm in (?:a )?crisis",
            r"keeps calm",
            r"stays calm",
            r"calmness under pressure",
            r"stress[- ]?resilien",
        ],
    },
    {
        "id": "c_understands_complicated_technology",
        "patterns": [r"understands complicated technology", r"complicated technology"],
    },
    {
        "id": "c_concern_for_others",
        "patterns": [r"concern for others", r"puts concern for others"],
    },
    {
        "id": "c_excellent_attention",
        "patterns": [r"excellent attention", r"attention skills"],
    },
]

METADATA_BLOCK_RE = re.compile(r"METADATA_JSON:\s*\{.*?\}", re.DOTALL)
HEADING_RE = re.compile(
    r"^## Round (?P<round>\d+) - (?P<label>.+?)\s*$",
    re.MULTILINE,
)
CANDIDATE_REFERENCE_RE = re.compile(
    r"\b(?:Candidate\s*[A-D]|[A-D]['’]s)\b",
    re.IGNORECASE,
)
RESPONSE_INTEGRATION_RE = re.compile(
    r"\b(?:new (?:input|information|observations?)|clarification|"
    r"additional (?:input|information|concerns?)|"
    r"as (?:agent\s*\d|you|sarah|james|emily|sofia) "
    r"(?:noted|mentioned|confirmed|highlighted|pointed out|reported|provided)|"
    r"(?:agent\s*\d|sarah|james|emily|sofia)['’]s "
    r"(?:input|information|clarification|point|assessment|observations?)|"
    r"from (?:agent\s*\d|sarah|james|emily|sofia)|"
    r"(?:confirms|confirmed by|reinforces|builds on|building on))\b",
    re.IGNORECASE,
)

OBSOLETE_TEAM_PROCESS_KEYS = (
    "team_process_method",
    "team_process_strategy_coordination",
    "team_process_private_fact_coverage",
    "team_process_criterion_coverage",
    "team_process_participation_balance",
    "team_process_evidence_integration",
    "team_process_decisive_evidence_uptake",
    "team_process_focused_question_share",
    "team_process_inquiry_network_coverage",
    "team_process_discussion_structure",
    "team_process_candidate_coverage",
    "team_process_responsiveness",
    "team_process_constructive_challenge",
    "team_process_agreement_building",
    "team_process_consensus_quality",
)


def read_json(path: Path) -> dict[str, Any]:
    """Read one metadata file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write one metadata file in the project's deterministic style."""
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def normalize_text(text: str) -> str:
    """Normalize text for pattern matching."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u202f", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def ratio(numerator: float, denominator: float) -> float:
    """Return a bounded ratio."""
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def parse_chat(path: Path) -> list[dict[str, Any]]:
    """Parse the public Markdown transcript produced by the simulation."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = list(HEADING_RE.finditer(text))
    messages: list[dict[str, Any]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = normalize_text(METADATA_BLOCK_RE.sub("", text[start:end]))
        if not body:
            continue

        label = normalize_text(match.group("label"))
        is_tool = label.lower().startswith("tool:")
        speaker = label
        if not is_tool:
            agent_match = re.search(r"Agent\s+(\d+)", label, re.IGNORECASE)
            if agent_match:
                speaker = f"agent_{agent_match.group(1)}"

        messages.append(
            {
                "speaker": speaker,
                "is_tool_exchange": is_tool,
                "text": body,
            }
        )

    return messages


def read_transcript_messages(run_dir: Path) -> tuple[list[dict[str, Any]], str]:
    """Read public transcript messages for one run."""
    chat_path = run_dir / "chat.md"
    if chat_path.exists():
        messages = parse_chat(chat_path)
        if messages:
            return messages, "chat.md"
    return [], "not_found"


def candidate_reference_spans(text: str, candidate: str) -> list[tuple[int, int]]:
    """Return spans where the message refers to a candidate label."""
    spans: list[tuple[int, int]] = []
    candidate_word = re.compile(rf"\bCandidate\s*{re.escape(candidate)}\b", re.IGNORECASE)
    candidate_letter = re.compile(rf"\b{re.escape(candidate)}(?:['’]s)?\b")
    for pattern in (candidate_word, candidate_letter):
        spans.extend(match.span() for match in pattern.finditer(text))
    return spans


def candidate_scoped_match(
    text: str,
    candidate: str,
    pattern: re.Pattern[str],
    window: int = 180,
) -> bool:
    """Return whether a fact pattern appears near the relevant candidate."""
    references = candidate_reference_spans(text, candidate)
    if not references:
        return False

    for match in pattern.finditer(text):
        match_start, match_end = match.span()
        for ref_start, ref_end in references:
            if match_end < ref_start - window or match_start > ref_end + window:
                continue
            return True
    return False


def decisive_evidence_uptake(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure the share of decisive Candidate C facts taken up by the team."""
    agent_mentions_by_fact: dict[str, set[str]] = {
        str(fact["id"]): set()
        for fact in DECISIVE_C_FACTS
    }

    for fact in DECISIVE_C_FACTS:
        fact_id = str(fact["id"])
        patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in fact["patterns"]
        ]
        for message in messages:
            if message["is_tool_exchange"]:
                continue
            speaker = str(message["speaker"])
            if speaker not in AGENT_LABELS:
                continue
            if any(
                candidate_scoped_match(message["text"], "C", pattern)
                for pattern in patterns
            ):
                agent_mentions_by_fact[fact_id].add(speaker)

    shared_fact_ids = sorted(
        fact_id
        for fact_id, agents in agent_mentions_by_fact.items()
        if len(agents) >= 2
    )
    return {
        "score": ratio(len(shared_fact_ids), len(DECISIVE_C_FACTS)),
        "shared_fact_ids": shared_fact_ids,
        "agent_mentions_by_fact": {
            fact_id: sorted(agents)
            for fact_id, agents in sorted(agent_mentions_by_fact.items())
        },
        "matched_shared_facts": len(shared_fact_ids),
        "total_decisive_facts": len(DECISIVE_C_FACTS),
    }


def inquiry_network_coverage(messages: list[dict[str, Any]]) -> float:
    """Measure how many directed agent-question pairs appear publicly."""
    pairs: set[tuple[str, str]] = set()
    for message in messages:
        if not message["is_tool_exchange"]:
            continue
        match = re.search(
            r"Agent\s+(\d+)\s*->\s*Agent\s+(\d+)",
            message["speaker"],
            re.IGNORECASE,
        )
        if match:
            pairs.add((f"agent_{match.group(1)}", f"agent_{match.group(2)}"))
    return ratio(len(pairs), 6)


def response_integration(messages: list[dict[str, Any]]) -> float:
    """Measure how often agents build on others' candidate contributions."""
    agent_messages = [
        message
        for message in messages
        if not message["is_tool_exchange"] and message["speaker"] in AGENT_LABELS
    ]
    integrated_messages = sum(
        1
        for message in agent_messages
        if RESPONSE_INTEGRATION_RE.search(message["text"])
        and CANDIDATE_REFERENCE_RE.search(message["text"])
    )
    return ratio(integrated_messages, len(agent_messages))


def calculate_team_process(
    messages: list[dict[str, Any]],
    transcript_source: str,
) -> dict[str, Any]:
    """Calculate one score per Mathieu et al. team-process dimension."""
    agent_messages = [message for message in messages if not message["is_tool_exchange"]]
    decisive_uptake = decisive_evidence_uptake(messages)

    communication = float(decisive_uptake["score"])
    coordination = inquiry_network_coverage(messages)
    cooperation = response_integration(messages)
    score = (communication + coordination + cooperation) / 3

    return {
        "score": round(score, 6),
        "dimensions": {
            "communication": round(communication, 6),
            "coordination": round(coordination, 6),
            "cooperation": round(cooperation, 6),
        },
        "decisive_evidence_uptake": {
            "score": round(communication, 6),
            "shared_fact_ids": decisive_uptake["shared_fact_ids"],
            "agent_mentions_by_fact": decisive_uptake["agent_mentions_by_fact"],
            "matched_shared_facts": decisive_uptake["matched_shared_facts"],
            "total_decisive_facts": decisive_uptake["total_decisive_facts"],
            "definition": (
                "share of decisive Candidate C facts mentioned by at least "
                "two discussion agents"
            ),
        },
        "coding": {
            "transcript_source": transcript_source,
            "transcript_message_count": len(messages),
            "agent_message_count": len(agent_messages),
            "tool_exchange_count": len(messages) - len(agent_messages),
            "uses_outcome_variables": False,
            "uses_efficiency_variables": False,
        },
    }


def has_current_team_process(metadata: dict[str, Any]) -> bool:
    """Return whether lean team-process metrics already exist."""
    detail = metadata.get("team_process")
    dimensions = detail.get("dimensions") if isinstance(detail, dict) else {}
    return (
        metadata.get("team_process_score") is not None
        and isinstance(dimensions, dict)
        and set(dimensions) == {"communication", "coordination", "cooperation"}
        and not any(key in metadata for key in OBSOLETE_TEAM_PROCESS_KEYS)
    )


def remove_obsolete_team_process_fields(metadata: dict[str, Any]) -> None:
    """Remove fields from the old many-indicator team-process metric."""
    for key in OBSOLETE_TEAM_PROCESS_KEYS:
        metadata.pop(key, None)


def update_metadata(metadata_path: Path, force: bool, verbose: bool) -> str:
    """Calculate one run's team-process metrics and write metadata."""
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        return "skipped_invalid_metadata"
    if metadata.get("status") != "completed":
        return "skipped_incomplete"
    if has_current_team_process(metadata) and not force:
        return "skipped_existing"

    messages, transcript_source = read_transcript_messages(metadata_path.parent)
    if not messages:
        return "skipped_no_transcript"

    team_process = calculate_team_process(messages, transcript_source)
    dimensions = team_process["dimensions"]
    remove_obsolete_team_process_fields(metadata)
    metadata.update(
        {
            "team_process_score": team_process["score"],
            "team_process_communication": dimensions["communication"],
            "team_process_coordination": dimensions["coordination"],
            "team_process_cooperation": dimensions["cooperation"],
            "team_process": team_process,
        }
    )
    write_json(metadata_path, metadata)

    if verbose:
        print(
            f"{metadata_path.parent.name}: "
            f"score={team_process['score']:.3f}, "
            f"communication={dimensions['communication']:.3f}, "
            f"coordination={dimensions['coordination']:.3f}, "
            f"cooperation={dimensions['cooperation']:.3f}"
        )
    return "updated"


def metadata_paths_from_args(args: argparse.Namespace) -> list[Path]:
    """Return metadata paths selected by command-line arguments."""
    if args.metadata:
        return [args.metadata]

    paths = sorted(args.input_root.glob("**/metadata.json"))
    if args.limit is not None:
        paths = paths[: max(0, args.limit)]
    return paths


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Calculate Mathieu-style team-process metrics from public "
            "transcripts and write them to metadata.json files."
        )
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Process one specific metadata.json file instead of an input root.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many metadata files; useful for testing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute metrics even when current metrics exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count eligible files without writing metadata.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print one result line per updated run.",
    )
    return parser.parse_args()


def main() -> int:
    """Calculate team-process metrics for selected simulation runs."""
    args = parse_args()
    metadata_paths = metadata_paths_from_args(args)
    counts: dict[str, int] = {}

    def count(action: str) -> None:
        counts[action] = counts.get(action, 0) + 1

    if args.dry_run:
        eligible = 0
        for path in metadata_paths:
            try:
                metadata = read_json(path)
            except Exception:
                count("skipped_invalid_metadata")
                continue
            if metadata.get("status") != "completed":
                count("skipped_incomplete")
            elif has_current_team_process(metadata) and not args.force:
                count("skipped_existing")
            elif not (path.parent / "chat.md").exists():
                count("skipped_no_transcript")
            else:
                eligible += 1

        print(f"Eligible metadata files: {eligible} of {len(metadata_paths)}")
        if counts:
            print(", ".join(f"{key}: {value}" for key, value in sorted(counts.items())))
        return 0

    for path in metadata_paths:
        try:
            action = update_metadata(path, force=args.force, verbose=args.verbose)
        except Exception as exc:
            action = "failed"
            print(f"ERROR {path}: {exc}", file=sys.stderr)
        count(action)

    summary = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    print(f"Processed team-process metrics ({summary})")
    return 1 if counts.get("failed", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
