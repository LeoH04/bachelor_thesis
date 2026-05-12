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
from .run_warnings import record_run_warning
from .gold_standard_alignment import (
    FACT_SOURCE_BUCKETS,
    calculate_gold_standard_alignment,
)
from .similarity import calculate_memory_similarity
from .smm import explicit_smm_memory_enabled
from .smm_sections import (
    SECTION_ORDER,
    parse_marked_sections,
    render_marked_memory,
)
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
    candidates = TASK["candidates"]
    goal = TASK["goal"]

    revealed_fact_rows = "\n".join(
        f"| {key} |  |  |  |  |" for key in AGENT_KEYS
    )
    candidate_rows = "\n".join(
        f"| {candidate} |  |  |  |  |" for candidate in candidates
    )
    agent_position_rows = "\n".join(
        f"| {key} | Unknown |  |  |  |" for key in AGENT_KEYS
    )

    title = f"# Shared Mental Model (Agent {agent_key.split('_')[-1]})"
    sections = {
        "task_summary": (
            "Goal\n"
            f"{goal}\n\n"
            "Candidates\n"
            f"{_as_bullets(candidates)}"
        ),
        "revealed_facts_by_source": (
            "| Source Agent | Candidate | Revealed Fact | Supports / Hurts | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{revealed_fact_rows}"
        ),
        "candidate_evaluation": (
            "| Candidate | Evidence For | Evidence Against | Fit for Role | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{candidate_rows}"
        ),
        "my_position": (
            "My Last Vote\n"
            "- None\n\n"
            "My Current Working Favorite\n"
            "- Undecided\n\n"
            "My Rationale\n"
            "-\n\n"
            "Evidence That Could Change My Mind\n"
            "-\n\n"
            "Confidence (percent)\n"
            "-"
        ),
        "other_agents_positions": (
            "| Agent | Latest Vote | Current Favorite | Main Reason | Confidence / Uncertainty |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{agent_position_rows}"
        ),
        "emerging_group_view": (
            "Group-Leading Candidate\n"
            "- None\n\n"
            "Important Agreements\n"
            "-\n\n"
            "Important Disagreements / Tensions\n"
            "-\n\n"
            "Uncertainties\n"
            "-"
        ),
        "open_questions_next_step_focus": (
            "Missing evidence\n"
            "-\n\n"
            "What would change the decision\n"
            "-\n\n"
            "What to ask or look for next\n"
            "-"
        ),
    }
    return render_marked_memory(title, sections)


def read_agent_memory(agent_key: str) -> str:
    """Read an agent's memory file."""
    path = _agent_memory_path(agent_key)
    if not path.exists():
        template = build_memory_template(agent_key)
        write_agent_memory(agent_key, template)
        record_run_warning(
            "memory_file_missing_template_used",
            "Agent memory file was missing and was replaced with a fresh template.",
            agent=agent_key,
            round=metrics.loop_count + 1,
            path=str(path),
        )
        return template

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        template = build_memory_template(agent_key)
        write_agent_memory(agent_key, template)
        record_run_warning(
            "memory_file_empty_template_used",
            "Agent memory file was empty and was replaced with a fresh template.",
            agent=agent_key,
            round=metrics.loop_count + 1,
            path=str(path),
        )
        return template

    return content


def write_agent_memory(agent_key: str, content: str) -> None:
    """Persist a full replacement markdown memory for the given agent."""
    path = _agent_memory_path(agent_key)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _merge_marked_memory_update(agent_key: str, proposed_memory: str) -> str:
    """Merge model-proposed section bodies into the existing marked memory file."""
    previous_memory = read_agent_memory(agent_key)
    previous_sections = parse_marked_sections(previous_memory)
    proposed_sections = parse_marked_sections(proposed_memory)

    if not previous_sections:
        previous_memory = build_memory_template(agent_key)
        previous_sections = parse_marked_sections(previous_memory)
        record_run_warning(
            "memory_previous_missing_markers",
            "Existing memory had no section markers; a fresh marked template was used as the merge base.",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )

    if not proposed_sections:
        record_run_warning(
            "memory_update_missing_markers",
            "Passive memory update did not include section markers; previous memory was preserved.",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        return previous_memory

    missing_sections = [
        section_id for section_id in SECTION_ORDER if section_id not in proposed_sections
    ]
    if missing_sections:
        record_run_warning(
            "memory_update_incomplete_sections",
            "Passive memory update omitted marked sections; omitted sections were preserved from previous memory.",
            agent=agent_key,
            round=metrics.loop_count + 1,
            missing_sections=missing_sections,
        )

    merged_sections = {
        section_id: proposed_sections.get(
            section_id,
            previous_sections.get(section_id, ""),
        )
        for section_id in SECTION_ORDER
    }
    title = previous_memory.splitlines()[0] if previous_memory.splitlines() else (
        f"# Shared Mental Model (Agent {agent_key.split('_')[-1]})"
    )
    return render_marked_memory(title, merged_sections)


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


def _fact_source_metadata(alignment: dict[str, object]) -> dict[str, object]:
    """Return run-level fact-source metrics for metadata output."""
    fields = {}
    for bucket in FACT_SOURCE_BUCKETS:
        fields[f"mean_{bucket}_facts"] = alignment.get(f"mean_{bucket}_facts")
        fields[f"mean_{bucket}_fact_coverage"] = alignment.get(
            f"mean_{bucket}_fact_coverage"
        )
    return fields


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
                **_fact_source_metadata({}),
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
    missing_agents = []
    empty_agents = []
    for agent_key in AGENT_KEYS:
        source = _agent_memory_path(agent_key)
        if not source.exists():
            missing_agents.append(agent_key)
            record_run_warning(
                "memory_archive_missing_file",
                "Agent memory file was missing during final archive.",
                agent=agent_key,
                round=metrics.loop_count,
                path=str(source),
            )
            continue

        target = destination / source.name
        shutil.copy2(source, target)
        copied_files.append(str(target))
        text = target.read_text(encoding="utf-8")
        if not text.strip():
            empty_agents.append(agent_key)
            record_run_warning(
                "memory_archive_empty_file",
                "Agent memory file was empty during final archive.",
                agent=agent_key,
                round=metrics.loop_count,
                path=str(source),
            )
            continue

        memory_texts[agent_key] = text

    if len(memory_texts) < len(AGENT_KEYS):
        record_run_warning(
            "context_metrics_incomplete_memories",
            "Context similarity and alignment metrics were computed with fewer memories than configured agents.",
            round=metrics.loop_count,
            expected_memory_count=len(AGENT_KEYS),
            usable_memory_count=len(memory_texts),
            missing_agents=missing_agents,
            empty_agents=empty_agents,
        )

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
            **_fact_source_metadata(gold_standard_alignment),
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
        path = _agent_memory_path(agent_key)
        if not path.exists():
            record_run_warning(
                "memory_reset_missing_template_used",
                "Agent memory file was missing before reset and was replaced with a fresh template.",
                agent=agent_key,
                round=metrics.loop_count + 1,
                path=str(path),
            )
        elif not path.read_text(encoding="utf-8").strip():
            record_run_warning(
                "memory_reset_empty_template_used",
                "Agent memory file was empty before reset and was replaced with a fresh template.",
                agent=agent_key,
                round=metrics.loop_count + 1,
                path=str(path),
            )

        template = build_memory_template(agent_key)
        write_agent_memory(agent_key, template)


def record_memory_update_response(agent_key: str, _callback_context, llm_response):
    """Persist a passive memory update from plain markdown model output."""
    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    visible_parts = _drop_thought_parts(parts)
    text = _visible_text_from_parts(visible_parts)
    memory = _extract_memory_markdown(text)

    if not memory:
        record_run_warning(
            "memory_update_empty",
            "Passive memory update returned no usable memory content.",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        log_event(
            "memory_update_missing",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        _replace_response_text(llm_response, "MEMORY_UPDATE_EMPTY")
        return llm_response

    memory = _merge_marked_memory_update(agent_key, memory)
    write_agent_memory(agent_key, memory)
    metrics.record_memory_update()
    log_event(
        "memory_updated",
        agent=agent_key,
        round=metrics.loop_count + 1,
    )
    _replace_response_text(llm_response, "MEMORY_UPDATED")
    return llm_response
