"""Build, persist, reset, and archive agent memories."""

import re
import shutil
from pathlib import Path

from .make_session_log import SHARED_MENTAL_MODELS_DIR, update_run_metadata
from .metrics import metrics
from .response_text import (
    MEMORY_MARKDOWN_PREFIX_RE,
    _drop_thought_parts,
    _replace_response_text,
    _visible_text_from_parts,
)
from .gold_standard_alignment import calculate_gold_standard_alignment
from .similarity import calculate_memory_similarity
from .smm import explicit_smm_memory_enabled
from .task import AGENT_KEYS, PROJECT_ROOT, TASK, _as_bullets
from .trace import log_event

_AGENT_MEMORIES_ARCHIVED = False


def _agent_memory_path(agent_key: str) -> Path:
    """Return the markdown memory file path for the given agent key."""
    return PROJECT_ROOT / "agents" / "discussion" / f"{agent_key}.md"


def _extract_memory_markdown(text: str) -> str:
    """Normalize a passive memory update response to raw markdown."""
    text = text.strip()
    text = MEMORY_MARKDOWN_PREFIX_RE.sub("", text)
    fence_match = re.search(r"```(?:markdown|md)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def build_memory_template(agent_key: str) -> str:
    """Create the initial structured markdown memory for one agent."""
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    candidate_rows = "\n".join(
        f"| {candidate} |  |  |  |  |" for candidate in candidates
    )
    agent_position_rows = "\n".join(
        f"| {key} | Unknown |  |  |" for key in AGENT_KEYS
    )

    return (
        f"# Shared Mental Model (Agent {agent_key.split('_')[-1]})\n\n"
        "## Task Summary\n"
        f"Goal\n{goal}\n\n"
        f"Candidates\n{_as_bullets(candidates)}\n\n"
        "## Candidate Summary Table\n"
        "| Candidate | Evidence For | Evidence Against | Fit for Role | Notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{candidate_rows}\n\n"
        "## My Position\n"
        "My Last Vote\n- None\n\n"
        "My Current Working Favorite\n- Undecided\n\n"
        "My Rationale\n-\n\n"
        "Evidence That Could Change My Mind\n-\n\n"
        "Confidence (percent)\n-\n\n"
        "## Other Agents' Positions\n"
        "| Agent | Latest Vote | Main Reason | Evidence Shared |\n"
        "| --- | --- | --- | --- |\n"
        f"{agent_position_rows}\n\n"
        "## Emerging Group View\n"
        "Group-Leading Candidate\n- None\n\n"
        "Important Agreements\n-\n\n"
        "Important Disagreements / Tensions\n-\n\n"
        "Uncertainties\n-\n\n"
        "## Open Questions\n"
        "Missing evidence\n-\n\n"
        "What would change the decision\n-\n\n"
        "## Next-Step Focus\n"
        "What to ask or look for next\n-\n"
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
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _context_alignment_score(
    mean_pairwise_similarity: object,
    mean_gold_standard_alignment: object,
) -> float | None:
    """Return the product of pairwise similarity and gold-standard alignment."""
    if mean_pairwise_similarity is None or mean_gold_standard_alignment is None:
        return None
    return round(
        float(mean_pairwise_similarity) * float(mean_gold_standard_alignment),
        6,
    )


def archive_agent_memories() -> Path | None:
    """Copy final agent memory markdown files into raw shared-mental-model data."""
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
                "gold_standard_alignment": [],
                "mean_gold_standard_alignment": None,
                "min_gold_standard_alignment": None,
                "max_gold_standard_alignment": None,
                "context_alignment": None,
                "gold_standard_alignment_method": "not_applicable",
            }
        )
        log_event(
            "context_consistency_not_applicable",
            reason=similarity["reason"],
        )
        return None

    destination.mkdir(parents=True, exist_ok=True)

    copied_files = []
    memory_texts = {}
    for agent_key in AGENT_KEYS:
        source = _agent_memory_path(agent_key)
        if source.exists():
            target = destination / source.name
            shutil.copy2(source, target)
            copied_files.append(str(target))
            memory_texts[agent_key] = target.read_text(encoding="utf-8")

    similarity = calculate_memory_similarity(memory_texts)
    gold_standard_alignment = calculate_gold_standard_alignment(memory_texts)
    mean_pairwise_similarity = similarity.get("mean_pairwise_similarity")
    mean_gold_standard_alignment = gold_standard_alignment.get("mean_alignment")

    _AGENT_MEMORIES_ARCHIVED = True
    update_run_metadata(
        {
            "shared_mental_models_archived": True,
            "shared_mental_model_files": copied_files,
            "context_consistency": similarity,
            "pairwise_memory_similarity": similarity.get("pairwise", []),
            "mean_pairwise_memory_similarity": mean_pairwise_similarity,
            "gold_standard_alignment": gold_standard_alignment.get("by_agent", []),
            "mean_gold_standard_alignment": mean_gold_standard_alignment,
            "min_gold_standard_alignment": gold_standard_alignment.get("min_alignment"),
            "max_gold_standard_alignment": gold_standard_alignment.get("max_alignment"),
            "context_alignment": _context_alignment_score(
                mean_pairwise_similarity,
                mean_gold_standard_alignment,
            ),
            "gold_standard_alignment_method": gold_standard_alignment.get("method"),
        }
    )
    log_event(
        "context_consistency_calculated",
        method=similarity.get("method"),
        mean_pairwise_similarity=similarity.get("mean_pairwise_similarity"),
        pairwise=similarity.get("pairwise", []),
    )
    log_event(
        "gold_standard_alignment_calculated",
        method=gold_standard_alignment.get("method"),
        mean_alignment=gold_standard_alignment.get("mean_alignment"),
        by_agent=gold_standard_alignment.get("by_agent", []),
    )
    return destination


def reset_all_agent_memories() -> None:
    """Reset every agent memory file to a fresh template."""
    for agent_key in AGENT_KEYS:
        template = build_memory_template(agent_key)
        write_agent_memory(agent_key, template)


def record_memory_update_response(agent_key: str, _callback_context, llm_response):
    """Persist a passive memory update from plain markdown model output."""
    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    visible_parts = _drop_thought_parts(content, parts)
    text = _visible_text_from_parts(visible_parts)
    memory = _extract_memory_markdown(text)

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
