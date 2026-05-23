"""Build, persist, initialize, and archive agent memories."""

import json
import re
from pathlib import Path

from .context_transparency import current_round_memory_scope_enabled
from .make_session_log import SHARED_MENTAL_MODELS_DIR, update_run_metadata
from .metrics import metrics
from .response_text import (
    MEMORY_MARKDOWN_PREFIX_RE,
    _drop_thought_parts,
    _replace_response_text,
    _visible_text_from_parts,
)
from .similarity import calculate_memory_similarity
from .smm import explicit_smm_memory_enabled
from .task import AGENT_KEYS, TASK
from .trace import log_event

_AGENT_MEMORIES_ARCHIVED = False

PILOT_CRITERIA = (
    "Reliability",
    "Stress resilience",
    "Technical competence",
    "Decision quality",
    "Attention and information accuracy",
    "Crew cooperation",
    "Professional communication",
    "Responsibility and role maturity",
    "Adaptability and feedback orientation",
)

MEMORY_SECTION_FIELDS = (
    ("candidate_evidence_table", "Candidate-Criterion Evidence Matrix"),
    ("information_disclosure_tracker", "Information Disclosure Tracker"),
    ("my_current_position", "My Current Position"),
    ("other_agents_positions", "Other Agents' Positions"),
    ("group_knowledge_state", "Group Knowledge State"),
)


def _agent_memory_path(agent_key: str) -> Path:
    """Return the markdown memory file path for the given agent key."""
    return SHARED_MENTAL_MODELS_DIR / f"{agent_key}.md"


def _render_memory_sections(agent_key: str, data: dict) -> str:
    """Render structured memory section bodies into the markdown memory document."""
    title = f"# Shared Mental Model (Agent {agent_key.split('_')[-1]})"
    sections = [title]
    for field, heading in MEMORY_SECTION_FIELDS:
        body = data.get(field)
        if not isinstance(body, str) or not body.strip():
            return ""
        sections.append(f"## {heading}\n{body.strip()}")
    return "\n\n".join(sections).strip()


def _extract_memory_markdown(agent_key: str, text: str) -> str:
    """Normalize a passive memory update JSON response to raw markdown."""
    text = text.strip()
    text = MEMORY_MARKDOWN_PREFIX_RE.sub("", text)

    json_text = text
    json_fence_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.DOTALL,
    )
    if json_fence_match:
        json_text = json_fence_match.group(1).strip()

    if json_text.startswith("{"):
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return ""

        if isinstance(data, dict):
            memory = data.get("memory_markdown")
            if isinstance(memory, str):
                return memory.strip()
            return _render_memory_sections(agent_key, data)
        return ""

    fence_match = re.search(r"```(?:markdown|md)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def build_memory_template(agent_key: str) -> str:
    """Create the initial structured markdown memory for one agent."""
    candidates = TASK.get("candidates", [])

    candidate_rows = "\n".join(
        f"| {candidate} | {criterion} |  |  | Unknown |  |  |  |"
        for candidate in candidates
        for criterion in PILOT_CRITERIA
    )
    disclosure_rows = "\n".join(
        f"| Agent {key.split('_')[-1]} | - |" for key in AGENT_KEYS
    )
    other_agent_rows = "\n".join(
        f"| Agent {key.split('_')[-1]} | - | - | - |"
        for key in AGENT_KEYS
        if key != agent_key
    )

    return (
        f"# Shared Mental Model (Agent {agent_key.split('_')[-1]})\n\n"
        "## Candidate-Criterion Evidence Matrix\n"
        "| Candidate | Criterion | Discussed evidence | Counterevidence or concern | Unknown or unclear | Evidence I know not yet discussed | Likely knowledge owner | Next best question |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"{candidate_rows}\n\n"
        "## Information Disclosure Tracker\n"
        "| Agent | What they have shared so far |\n"
        "| --- | --- |\n"
        f"{disclosure_rows}\n\n"
        "## My Current Position\n"
        "Current vote: -\n"
        "Main reason: -\n"
        "Confidence: -\n"
        "What would change my mind: -\n\n"
        "## Other Agents' Positions\n"
        "| Agent | Last vote | Stated reason | What they have revealed so far |\n"
        "| --- | --- | --- | --- |\n"
        f"{other_agent_rows}\n\n"
        "## Group Knowledge State\n"
        "What the group has collectively established: -\n"
        "What remains contested: -\n"
        "What information is still missing from discussion: -\n"
        "Consensus readiness based on available evidence: -\n"
    )


def read_agent_memory(agent_key: str) -> str:
    """Read an agent's memory file, falling back to a fresh template if needed."""
    path = _agent_memory_path(agent_key)
    if not path.exists():
        return build_memory_template(agent_key)

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return build_memory_template(agent_key)

    return content


def write_agent_memory(agent_key: str, content: str) -> None:
    """Persist a full replacement markdown memory for the given agent."""
    path = _agent_memory_path(agent_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def archive_agent_memories() -> Path | None:
    """Finalize run-local agent memory markdown files and calculate metrics."""
    global _AGENT_MEMORIES_ARCHIVED

    destination = SHARED_MENTAL_MODELS_DIR
    if _AGENT_MEMORIES_ARCHIVED:
        return None

    if not explicit_smm_memory_enabled():
        similarity = {
            "method": "not_applicable",
            "reason": "explicit_smm_memory_disabled",
            "agent_count": 0,
            "pairwise": [],
            "mean_pairwise_similarity": None,
            "min_pairwise_similarity": None,
            "max_pairwise_similarity": None,
        }
        _AGENT_MEMORIES_ARCHIVED = True
        update_run_metadata(
            {
                "shared_mental_models_archived": False,
                "shared_mental_model_files": [],
                "context_consistency": similarity,
                "pairwise_memory_similarity": [],
                "mean_pairwise_memory_similarity": None,
            }
        )
        log_event(
            "context_consistency_not_applicable",
            reason=similarity["reason"],
        )
        return None

    destination.mkdir(parents=True, exist_ok=True)

    memory_files = []
    memory_texts = {}
    for agent_key in AGENT_KEYS:
        source = _agent_memory_path(agent_key)
        if source.exists():
            memory_files.append(str(source))
            memory_texts[agent_key] = source.read_text(encoding="utf-8")

    similarity = calculate_memory_similarity(memory_texts)

    _AGENT_MEMORIES_ARCHIVED = True
    update_run_metadata(
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
    log_event(
        "context_consistency_calculated",
        method=similarity.get("method"),
        mean_pairwise_similarity=similarity.get("mean_pairwise_similarity"),
        pairwise=similarity.get("pairwise", []),
    )
    return destination


def initialize_all_agent_memories() -> None:
    """Initialize every run-local agent memory file with a fresh template."""
    if not explicit_smm_memory_enabled():
        return

    for agent_key in AGENT_KEYS:
        template = build_memory_template(agent_key)
        write_agent_memory(agent_key, template)


def reset_agent_memories_for_current_round(round_number: int | None = None) -> bool:
    """Reset treatment memories when low input transparency limits context by round."""
    if not explicit_smm_memory_enabled() or not current_round_memory_scope_enabled():
        return False

    initialize_all_agent_memories()
    log_event(
        "round_memory_reset",
        round=round_number or metrics.loop_count + 1,
        reason="low_input_transparency_current_round_scope",
    )
    return True


def record_memory_update_response(agent_key: str, _callback_context, llm_response):
    """Persist a passive memory update from plain markdown model output."""
    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    visible_parts = _drop_thought_parts(content, parts)
    text = _visible_text_from_parts(visible_parts)
    memory = _extract_memory_markdown(agent_key, text)

    if not memory:
        log_event(
            "memory_update_missing",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        _replace_response_text(llm_response, "MEMORY_UPDATE_EMPTY")
        return llm_response

    write_agent_memory(agent_key, memory)
    metrics.record_memory_update()
    log_event(
        "memory_updated",
        agent=agent_key,
        round=metrics.loop_count + 1,
    )
    _replace_response_text(llm_response, "MEMORY_UPDATED")
    return llm_response
