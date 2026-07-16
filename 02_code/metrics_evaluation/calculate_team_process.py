#!/usr/bin/env python3
"""Calculate transcript-based team-process metrics for simulation runs.

Each dimension is represented by one public-transcript indicator:

- communication: uptake of initially private candidate facts
- coordination: completed question-answer-use sequences
- cooperation: substantive integration of another agent's contribution

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
DEFAULT_INPUT_ROOT = REPO_ROOT / "01_data" / "raw" / "simulations"

AGENT_LABELS = ("agent_1", "agent_2", "agent_3")
TEAM_PROCESS_METHOD = "private_uptake_completed_coordination_integration_v2"

PRIVATE_FACTS: list[dict[str, Any]] = [
    {
        "id": "a_takes_criticism_poorly",
        "candidate": "A",
        "patterns": [
            r"(?:not good at|struggles? with|poor at) (?:taking|accepting) criticism",
            r"resistant to criticism",
        ],
    },
    {
        "id": "a_unorganized",
        "candidate": "A",
        "patterns": [r"unorgani[sz]ed", r"disorgani[sz]ed"],
    },
    {
        "id": "a_show_off",
        "candidate": "A",
        "patterns": [r"show[- ]?off"],
    },
    {
        "id": "a_not_open_to_new_ideas",
        "candidate": "A",
        "patterns": [r"not open to new ideas", r"resistant to new ideas"],
    },
    {
        "id": "a_unfriendly",
        "candidate": "A",
        "patterns": [r"unfriendly"],
    },
    {
        "id": "a_unhealthy_eating",
        "candidate": "A",
        "patterns": [r"eats? unhealthily", r"unhealthy (?:diet|eating)"],
    },
    {
        "id": "b_grumpy",
        "candidate": "B",
        "patterns": [r"grumpy"],
    },
    {
        "id": "b_uncooperative",
        "candidate": "B",
        "patterns": [r"uncooperative", r"not cooperative"],
    },
    {
        "id": "b_weak_numeric_memory",
        "candidate": "B",
        "patterns": [
            r"weak (?:memory|numeric memory) for numbers",
            r"weak numeric(?:al)? memory",
            r"numeric[- ]memory (?:deficit|weakness)",
            r"poor (?:memory )?for numbers",
        ],
    },
    {
        "id": "b_nasty_remarks",
        "candidate": "B",
        "patterns": [r"nasty remarks?", r"derogatory remarks?"],
    },
    {
        "id": "b_pretentious",
        "candidate": "B",
        "patterns": [r"pretentious"],
    },
    {
        "id": "b_wrong_tone",
        "candidate": "B",
        "patterns": [r"wrong tone", r"inappropriate tone"],
    },
    {
        "id": "c_100_percent_reliable",
        "candidate": "C",
        "patterns": [r"100\s*(?:%|percent) reliable", r"completely reliable"],
    },
    {
        "id": "c_positive_crew_atmosphere",
        "candidate": "C",
        "patterns": [r"positive (?:crew )?atmosphere", r"atmosphere with (?:his|the) crew"],
    },
    {
        "id": "c_calm_in_crisis",
        "candidate": "C",
        "patterns": [
            r"calm in (?:a )?crisis",
            r"keeps calm",
            r"stays calm",
            r"calmness under pressure",
        ],
    },
    {
        "id": "c_understands_complicated_technology",
        "candidate": "C",
        "patterns": [r"understands complicated technology", r"complicated technology"],
    },
    {
        "id": "c_concern_for_others",
        "candidate": "C",
        "patterns": [r"concern for others", r"puts concern for others"],
    },
    {
        "id": "c_excellent_attention",
        "candidate": "C",
        "patterns": [r"excellent attention", r"attention skills"],
    },
    {
        "id": "d_arrogant",
        "candidate": "D",
        "patterns": [r"arrogant"],
    },
    {
        "id": "d_weak_leadership",
        "candidate": "D",
        "patterns": [
            r"weak leadership",
            r"leadership (?:skills? )?(?:is|are|seems?) (?:relatively )?weak",
        ],
    },
    {
        "id": "d_know_it_all",
        "candidate": "D",
        "patterns": [r"know[- ]?it[- ]?all"],
    },
    {
        "id": "d_hot_temper",
        "candidate": "D",
        "patterns": [r"hot temper"],
    },
    {
        "id": "d_moody",
        "candidate": "D",
        "patterns": [r"moody"],
    },
    {
        "id": "d_loner",
        "candidate": "D",
        "patterns": [r"loner"],
    },
]

PUBLIC_FACTS: list[dict[str, Any]] = [
    {"id": "a_anticipates_danger", "candidate": "A", "patterns": [r"anticipat(?:e|es|ing) dangerous situations"]},
    {"id": "a_complex_connections", "candidate": "A", "patterns": [r"(?:see|sees|understands?) complex connections"]},
    {"id": "a_spatial_vision", "candidate": "A", "patterns": [r"excellent spatial vision"]},
    {"id": "a_leadership", "candidate": "A", "patterns": [r"very good leadership"]},
    {"id": "b_conscientious", "candidate": "B", "patterns": [r"very conscientious"]},
    {
        "id": "b_handles_stress",
        "candidate": "B",
        "patterns": [r"handles? stress very well"],
    },
    {"id": "b_weather", "candidate": "B", "patterns": [r"good at assessing weather", r"assess(?:es|ing)? weather (?:conditions )?(?:well|accurately)"]},
    {"id": "b_computer_skills", "candidate": "B", "patterns": [r"excellent computer skills"]},
    {"id": "c_fast_decisions", "candidate": "C", "patterns": [r"(?:make|makes|making) correct decisions quick(?:ly)?"]},
    {"id": "c_communication_difficulty", "candidate": "C", "patterns": [r"difficulty communicating ideas"]},
    {"id": "c_egocentric", "candidate": "C", "patterns": [r"egocentric"]},
    {"id": "c_education", "candidate": "C", "patterns": [r"not (?:very )?willing to further (?:his )?education", r"lack of willingness to further"]},
    {"id": "d_unexpected_events", "candidate": "D", "patterns": [r"responds? to unexpected events adequately"]},
    {"id": "d_concentration", "candidate": "D", "patterns": [r"concentrat(?:e|es|ion) very well", r"strong concentration"]},
    {"id": "d_problem_solving", "candidate": "D", "patterns": [r"solves? problems? extremely well", r"strong problem.solving"]},
    {"id": "d_responsibility", "candidate": "D", "patterns": [r"takes? responsibility seriously"]},
]

ALL_CANDIDATE_FACTS = PRIVATE_FACTS + PUBLIC_FACTS

METADATA_BLOCK_RE = re.compile(r"\**METADATA_JSON:\**\s*\{.*?\}", re.DOTALL)
HEADING_RE = re.compile(
    r"^## Round (?P<round>\d+) - (?P<label>.+?)\s*$",
    re.MULTILINE,
)
CANDIDATE_REFERENCE_RE = re.compile(
    r"\b(?:Candidates?\s*[A-D]|[A-D]['’]s)\b",
    re.IGNORECASE,
)
AGENT_REFERENCE = r"(?:Agent\s*[123]|Sarah|James|Emily|Anna|Markus|Sofia)"
RESPONSE_INTEGRATION_RE = re.compile(
    rf"""\b(?:
        I\s+(?:appreciate|agree|concur)\s+with\s+(?:
            {AGENT_REFERENCE}|the\s+(?:panel|group)|
            (?:the\s+)?(?:earlier|previous|current)?\s*
            (?:assessment|point|position|recommendation)s?
        )|
        I\s+appreciate\s+(?:{AGENT_REFERENCE}['’]s|the|your|these|those)\s+
            (?:assessment|point|input|information|clarification|contribution|argument|evidence)s?|
        (?:building|builds?|drawing)\s+on|
        (?:as|like)\s+{AGENT_REFERENCE}\s+
            (?:noted|mentioned|confirmed|highlighted|pointed\s+out|reported|provided|argued)|
        {AGENT_REFERENCE}['’]s\s+
            (?:input|information|clarification|point|assessment|observations?|emphasis|concern|argument)|
        {AGENT_REFERENCE}\s+
            (?:noted|mentioned|confirmed|highlighted|pointed\s+out|reported|provided|argued|raised|emphasi[sz]ed)|
        (?:point|concern|assessment|argument|evidence|observation)s?\s+
            (?:raised|made|provided|highlighted|noted)\s+by\s+{AGENT_REFERENCE}|
        (?:confirm|reinforc|support)s?(?:ed)?\s+by\s+{AGENT_REFERENCE}|
        (?:the|our)\s+(?:panel|group)['’]s\s+(?:assessment|discussion|view|position)|
        (?:earlier|previous)\s+(?:assessment|point|discussion|contribution)s?|
        points?\s+raised
    )\b""",
    re.IGNORECASE | re.VERBOSE,
)

NO_EVIDENCE_RE = re.compile(
    r"\b(?:do not have|does not have|have no|has no|"
    r"no (?:direct|specific|documented|clear|concrete|explicit)?\s*"
    r"(?:evidence|information|data|observations?|examples?)|"
    r"lack(?:s|ing)? (?:of )?(?:direct |specific |concrete )?"
    r"(?:evidence|information|data|observations?))\b",
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
        caller = None
        target = None
        question = ""
        answer = ""
        if is_tool:
            tool_match = re.search(
                r"Agent\s+(\d+)\s*->\s*Agent\s+(\d+)",
                label,
                re.IGNORECASE,
            )
            if tool_match:
                caller = f"agent_{tool_match.group(1)}"
                target = f"agent_{tool_match.group(2)}"
            if "Question:" in body:
                question = body.split("Question:", 1)[1].split("Answer:", 1)[0].strip()
            if "Answer:" in body:
                answer = body.split("Answer:", 1)[1].strip()
        else:
            agent_match = re.search(r"Agent\s+(\d+)", label, re.IGNORECASE)
            if agent_match:
                speaker = f"agent_{agent_match.group(1)}"

        messages.append(
            {
                "speaker": speaker,
                "is_tool_exchange": is_tool,
                "round": int(match.group("round")),
                "caller": caller,
                "target": target,
                "question": question,
                "answer": answer,
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
    candidate_word = re.compile(rf"\bCandidates?\s*{re.escape(candidate)}\b", re.IGNORECASE)
    letter_suffix = r"['’]s" if candidate == "A" else r"(?:['’]s)?"
    candidate_letter = re.compile(rf"\b{re.escape(candidate)}{letter_suffix}\b")
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


def fact_matches(text: str, fact: dict[str, Any]) -> bool:
    """Return whether text contains one candidate-scoped canonical fact."""
    candidate = str(fact["candidate"])
    return any(
        candidate_scoped_match(
            text,
            candidate,
            re.compile(pattern, re.IGNORECASE),
        )
        for pattern in fact["patterns"]
    )


def public_utterances(messages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Expand messages into chronological public utterances with speakers."""
    utterances: list[tuple[str, str]] = []
    for message in messages:
        if message["is_tool_exchange"]:
            caller = message.get("caller")
            target = message.get("target")
            if caller in AGENT_LABELS and message.get("question"):
                utterances.append((str(caller), str(message["question"])))
            if target in AGENT_LABELS and message.get("answer"):
                utterances.append((str(target), str(message["answer"])))
        elif message["speaker"] in AGENT_LABELS:
            utterances.append((str(message["speaker"]), str(message["text"])))
    return utterances


def private_information_uptake(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure private facts subsequently used by a different agent."""
    utterances = public_utterances(messages)
    mentions_by_fact: dict[str, list[dict[str, Any]]] = {}
    uptake_fact_ids: list[str] = []
    disclosed_fact_ids: list[str] = []

    for fact in PRIVATE_FACTS:
        fact_id = str(fact["id"])
        mentions = [
            {"sequence": index, "agent": speaker}
            for index, (speaker, text) in enumerate(utterances)
            if fact_matches(text, fact)
        ]
        mentions_by_fact[fact_id] = mentions
        if mentions:
            disclosed_fact_ids.append(fact_id)
        if any(
            later["sequence"] > first["sequence"]
            and later["agent"] != first["agent"]
            for first in mentions
            for later in mentions
        ):
            uptake_fact_ids.append(fact_id)

    return {
        "score": ratio(len(uptake_fact_ids), len(PRIVATE_FACTS)),
        "uptake_fact_ids": sorted(uptake_fact_ids),
        "disclosed_fact_ids": sorted(disclosed_fact_ids),
        "mentions_by_fact": mentions_by_fact,
        "matched_uptake_facts": len(uptake_fact_ids),
        "matched_disclosed_facts": len(disclosed_fact_ids),
        "total_private_facts": len(PRIVATE_FACTS),
    }


def candidate_labels(text: str) -> set[str]:
    """Return explicitly named candidate letters."""
    labels = set(
        match.group(1).upper()
        for match in re.finditer(r"\bCandidates?\s*([A-D])\b", text, re.IGNORECASE)
    )
    labels.update(
        match.group(1).upper()
        for match in re.finditer(r"\b([A-D])['’]s\b", text, re.IGNORECASE)
    )
    labels.update(match.group(1) for match in re.finditer(r"\b([B-D])\b", text))
    for match in re.finditer(r"\bCandidates\b([^.!?;:]*)", text, re.IGNORECASE):
        labels.update(re.findall(r"\b[A-D]\b", match.group(1)))
    return labels


def tool_answer_use_reason(
    tool_message: dict[str, Any],
    agent_message: dict[str, Any],
) -> str | None:
    """Return why a caller's public message uses one tool answer."""
    question = str(tool_message.get("question") or "")
    answer = str(tool_message.get("answer") or "")
    public_text = str(agent_message["text"])
    relevant_candidates = candidate_labels(question) & candidate_labels(public_text)
    if not relevant_candidates:
        return None

    reused_facts = sorted(
        str(fact["id"])
        for fact in ALL_CANDIDATE_FACTS
        if str(fact["candidate"]) in relevant_candidates
        and fact_matches(answer, fact)
        and fact_matches(public_text, fact)
    )
    if reused_facts:
        return "fact_reuse:" + ",".join(reused_facts)

    for candidate in relevant_candidates:
        if candidate_scoped_match(answer, candidate, NO_EVIDENCE_RE) and candidate_scoped_match(
            public_text,
            candidate,
            NO_EVIDENCE_RE,
        ):
            return f"no_evidence_reuse:{candidate}"

    target = tool_message.get("target")
    if isinstance(target, str) and target.startswith("agent_"):
        target_number = target.rsplit("_", 1)[-1]
        if re.search(rf"\bAgent\s*{re.escape(target_number)}\b", public_text, re.IGNORECASE) and re.search(
            r"\b(?:confirm|clarif|report|provide|answer|response|input|information|according)\w*\b",
            public_text,
            re.IGNORECASE,
        ):
            return f"explicit_attribution:{target}"
    return None


def completed_information_coordination(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure agent turns containing a completed question-answer-use sequence."""
    agent_messages = [
        message
        for message in messages
        if not message["is_tool_exchange"] and message["speaker"] in AGENT_LABELS
    ]
    tools_by_turn: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for message in messages:
        caller = message.get("caller")
        if not message["is_tool_exchange"] or caller not in AGENT_LABELS:
            continue
        key = (int(message["round"]), str(caller))
        tools_by_turn.setdefault(key, []).append(message)

    completed_turns: list[dict[str, Any]] = []
    tool_turn_count = 0
    for message in agent_messages:
        key = (int(message["round"]), str(message["speaker"]))
        tool_messages = tools_by_turn.get(key, [])
        if not tool_messages:
            continue
        tool_turn_count += 1
        reasons = [
            reason
            for tool_message in tool_messages
            if (reason := tool_answer_use_reason(tool_message, message)) is not None
        ]
        if reasons:
            completed_turns.append(
                {
                    "round": message["round"],
                    "agent": message["speaker"],
                    "reasons": reasons,
                }
            )

    return {
        "score": ratio(len(completed_turns), len(agent_messages)),
        "completed_turn_count": len(completed_turns),
        "tool_turn_count": tool_turn_count,
        "agent_turn_count": len(agent_messages),
        "completed_turns": completed_turns,
    }


def collaborative_integration(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure substantive integration of another agent's contribution."""
    agent_messages = [
        message
        for message in messages
        if not message["is_tool_exchange"] and message["speaker"] in AGENT_LABELS
    ]
    eligible_messages = agent_messages[1:]
    integrated_messages = sum(
        1
        for message in eligible_messages
        if RESPONSE_INTEGRATION_RE.search(message["text"])
        and CANDIDATE_REFERENCE_RE.search(message["text"])
    )
    return {
        "score": ratio(integrated_messages, len(eligible_messages)),
        "integrated_message_count": integrated_messages,
        "eligible_message_count": len(eligible_messages),
    }


def calculate_team_process(
    messages: list[dict[str, Any]],
    transcript_source: str,
) -> dict[str, Any]:
    """Calculate one transcript-based score per team-process dimension."""
    agent_messages = [
        message
        for message in messages
        if not message["is_tool_exchange"] and message["speaker"] in AGENT_LABELS
    ]
    communication_detail = private_information_uptake(messages)
    coordination_detail = completed_information_coordination(messages)
    cooperation_detail = collaborative_integration(messages)

    communication = float(communication_detail["score"])
    coordination = float(coordination_detail["score"])
    cooperation = float(cooperation_detail["score"])
    score = (communication + coordination + cooperation) / 3

    return {
        "method": TEAM_PROCESS_METHOD,
        "score": round(score, 6),
        "dimensions": {
            "communication": round(communication, 6),
            "coordination": round(coordination, 6),
            "cooperation": round(cooperation, 6),
        },
        "private_information_uptake": {
            "score": round(communication, 6),
            **{key: value for key, value in communication_detail.items() if key != "score"},
            "definition": (
                "share of all initially private candidate facts subsequently "
                "used by a different agent"
            ),
        },
        "completed_information_coordination": {
            "score": round(coordination, 6),
            **{key: value for key, value in coordination_detail.items() if key != "score"},
            "definition": (
                "share of scheduled agent turns containing at least one "
                "completed question-answer-use sequence"
            ),
        },
        "collaborative_integration": {
            "score": round(cooperation, 6),
            **{key: value for key, value in cooperation_detail.items() if key != "score"},
            "definition": (
                "share of eligible agent messages that substantively integrate "
                "another agent's contribution"
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
    method = detail.get("method") if isinstance(detail, dict) else None
    return (
        metadata.get("team_process_score") is not None
        and isinstance(dimensions, dict)
        and set(dimensions) == {"communication", "coordination", "cooperation"}
        and method == TEAM_PROCESS_METHOD
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
