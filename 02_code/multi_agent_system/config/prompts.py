"""Build prompts for discussion, memory update, and tool-response agents."""

import os

from .history import _get_state, _round_number, build_public_discussion_history
from .memory import read_agent_memory
from .response_text import (
    METADATA_JSON_LABEL,
    PUBLIC_MESSAGE_LABEL,
    extract_vote_from_response,
)
from .smm import explicit_smm_memory_enabled
from .task import AGENT_KEYS, TASK, _as_bullets


TRANSPARENCY_POLICIES = {
    "low": {
        "discussion": (
            "LOW context transparency means public messages expose only the "
            "minimum decision context needed for coordination.\n"
            "Public contribution rules:\n"
            "- State your current preferred candidate.\n"
            "- Share at most one brief candidate fact, concern, or direct "
            "answer from the allowed evidence.\n"
            "- Keep role evaluation, comparisons, source/provenance labels, "
            "confidence estimates, uncertainty estimates, and references to "
            "prior discussion out of the public message unless needed to "
            "answer a direct question.\n"
            "- Do not use an explicit reasoning structure.\n"
            "Task-specific output rule: state your preferred candidate and "
            "one short candidate fact or concern, with no comparison or "
            "justification beyond that fact."
        ),
        "tool": (
            "LOW context transparency means public tool answers expose only the "
            "minimum useful answer.\n"
            "Answer with at most one brief fact, concern, or direct statement "
            "from the allowed evidence. Do not add reasoning structure, "
            "source/provenance labels, confidence, uncertainty, or comparisons."
        ),
        "public_template": (
            "<state your current preferred candidate and at most one brief candidate fact or concern>"
        ),
    },
    "moderate": {
        "discussion": (
            "MODERATE context transparency means public messages expose a "
            "compact, task-relevant version of your decision context.\n"
            "Public contribution rules:\n"
            "- State your current preferred candidate.\n"
            "- Share one or two candidate-linked facts or reasons from the "
            "allowed evidence.\n"
            "- Briefly state why those facts matter for the selection criteria.\n"
            "- Include one main tradeoff, uncertainty, or decision blocker if "
            "one is relevant.\n"
            "- Reference prior discussion only when it helps coordinate the "
            "current decision.\n"
            "- Do not provide exhaustive evidence lists, detailed source "
            "accounting, or long alternative analyses.\n"
            "Task-specific output rule: state your preferred candidate, give "
            "one or two candidate-linked facts, briefly connect them to the "
            "selection criteria, and name one tradeoff or unresolved issue."
        ),
        "tool": (
            "MODERATE context transparency means public tool answers provide "
            "compact, task-relevant context.\n"
            "Answer directly with one or two relevant facts or concerns from "
            "the allowed evidence. Link them to the candidate they affect and "
            "include a short role-relevance statement only if it helps the "
            "caller use the information."
        ),
        "public_template": (
            "<state your current preferred candidate; give one or two "
            "candidate-linked facts or reasons; briefly explain why they matter "
            "for the selection criteria; include one main tradeoff, uncertainty, "
            "or unresolved issue if relevant; "
            "avoid exhaustive reasoning summaries>"
        ),
    },
    "high": {
        "discussion": (
            "HIGH context transparency means public messages expose an expanded "
            "but bounded reasoning-context summary.\n"
            "Public contribution rules:\n"
            "- State your current preferred candidate.\n"
            "- Include confidence or uncertainty.\n"
            "- Link evidence to candidates and the selection criteria.\n"
            "- Distinguish information from your own candidate materials from "
            "information shared in the discussion.\n"
            "- Reference relevant prior discussion when it affects the current "
            "decision context.\n"
            "- Compare major alternatives and tradeoffs using only allowed "
            "evidence.\n"
            "- State unresolved uncertainties or missing group information that "
            "could affect your vote.\n"
            "- Do not expose raw hidden chain-of-thought. Provide only a concise, "
            "structured public reasoning summary.\n"
            "Task-specific output rule: include the required reasoning summary "
            "with Evidence from my materials, Evidence from discussion, "
            "Alternatives considered, Main tradeoff, Remaining uncertainty, and "
            "What could change my vote."
        ),
        "tool": (
            "HIGH context transparency means public tool answers expose a concise "
            "reasoning-context summary, not raw hidden chain-of-thought.\n"
            "Answer directly, identify whether the information comes from your "
            "own candidate materials or the prior discussion, mention uncertainty "
            "if relevant, and briefly explain how the answer affects the decision "
            "context."
        ),
        "public_template": (
            "Use this structure:\n"
            "Current position: <preferred candidate>\n"
            "Confidence/uncertainty: <brief estimate or qualitative uncertainty>\n"
            "Reasoning-context summary:\n"
            "- Evidence from my materials: <candidate evidence from your own materials>\n"
            "- Evidence from discussion: <relevant information shared by other agents>\n"
            "- Alternatives considered: <major alternatives and why they are weaker or still plausible based on allowed evidence>\n"
            "- Main tradeoff: <central decision tradeoff>\n"
            "- Remaining uncertainty: <main open issue>\n"
            "- What could change my vote: <specific missing or not-yet-shared task information that could affect the position>"
        ),
    },
}

def _context_transparency_condition() -> str:
    """Return the active context-transparency condition from SIM_CONDITION."""
    condition = os.getenv("SIM_CONDITION", "low").strip().lower()
    if condition not in TRANSPARENCY_POLICIES:
        valid = ", ".join(sorted(TRANSPARENCY_POLICIES))
        raise ValueError(
            f"Unsupported SIM_CONDITION={condition!r}. Expected one of: {valid}."
        )
    return condition


def _transparency_section(kind: str) -> str:
    """Build the condition-specific transparency instruction section."""
    condition = _context_transparency_condition()
    policy = TRANSPARENCY_POLICIES[condition][kind]
    return (
        "Context transparency policy:\n"
        "Operational definition: context transparency is the degree to which an "
        "agent externalizes its internal decision context into the shared "
        "communication space.\n"
        "Manipulation boundary: this policy controls only what you disclose "
        "publicly and how structured that disclosure is. Evaluate candidates "
        "using the same task goal and allowed evidence across all conditions. "
        "It does not change your cooperative goal to reach a common hiring "
        "decision.\n"
        f"Active condition: {condition}\n"
        f"{policy}"
    )

def _information_sharing_guidance() -> str:
    """Return condition-neutral guidance for sharing individual information."""
    return (
        "Use the discussion to exchange decision-relevant information, but apply "
        "the active context transparency policy to determine how much detail, "
        "candidate linkage, reasoning, source context, comparison, and uncertainty "
        "to disclose publicly."
    )

def _memory_guided_turn_section() -> str:
    """Return speaking-turn guidance for treatment-mode memory use."""
    if explicit_smm_memory_enabled():
        return (
            "Memory-guided speaking-turn use:\n"
            "Use the explicit shared mental model from the previous update phase "
            "to identify unresolved issues, missing decision-relevant information, "
            "and the next most useful contribution.\n"
            "Pay particular attention to the Open Questions (`open_questions`) "
            "and Next-Step Focus (`next_step_focus`) memory sections. If either "
            "section indicates a gap that could affect the final candidate choice, "
            "prioritize that gap either by asking a targeted agent-tool question "
            "or by addressing it in your public contribution, while staying within "
            "the active context transparency policy.\n"
            "Do not update memory during this speaking turn. Use memory only as "
            "context for deciding what to ask or say.\n\n"
        )

    return ""

def _public_message_template() -> str:
    """Return the output template for the active transparency condition."""
    condition = _context_transparency_condition()
    return TRANSPARENCY_POLICIES[condition]["public_template"]


def _latest_vote_for_agent(ctx, agent_key: str | None) -> str:
    """Return the latest recorded vote for an agent, or a placeholder."""
    if not agent_key:
        return "Unavailable"

    response = _get_state(ctx).get(f"{agent_key}_response", "")
    return extract_vote_from_response(response) or "Unavailable"


def _memory_context_section(agent_key: str) -> str:
    """Return explicit SMM memory, or nothing for baseline runs."""
    if explicit_smm_memory_enabled():
        return (
            "Previous internal memory:\n"
            f"{read_agent_memory(agent_key)}\n\n"
        )

    return ""


def _grounding_sources() -> str:
    """Return the allowed evidence sources for the active SMM mode."""
    if explicit_smm_memory_enabled():
        return (
            "candidate information, previous internal memory, or the discussion "
            "so far"
        )

    return "candidate information or the discussion so far"


def build_agent_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the full prompt for an agent's scheduled public discussion turn."""
    memory_context = _memory_context_section(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    current_round = _round_number()
    other_agents = [key for key in AGENT_KEYS if key != agent_key]
    other_agent_tools = [
        f"{key}_tool ({key.replace('_', ' ').title()})"
        for key in other_agents
    ]
    vote_options = "|".join(candidates) if candidates else "candidate"
    transparency_section = _transparency_section("discussion")
    public_message_template = _public_message_template()
    information_sharing_guidance = _information_sharing_guidance()
    memory_guided_turn = _memory_guided_turn_section()

    return (
    f"You are {agent_key.replace('_', ' ').title()}.\n\n"

    "You are a member of the personnel selection committee of an airline company.\n"
    "The airline is hiring a new pilot for long-distance flights.\n"
    "Your group must choose one of the candidates for this position.\n\n"

    "Task:\n"
    f"{goal}\n"
    f"Candidates: {', '.join(candidates)}\n"
    f"Current discussion round: {current_round}\n\n"

    "Information structure:\n"
    "You have received individual information about the candidates. Part of the "
    "information available to group members is identical, and part of it "
    "differs across group members. On the basis of the full information set held "
    "within the group, one candidate is clearly the best choice. Your group's task "
    "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

    "Information available to you:\n"
    "Public information known to all agents:\n"
        f"{_as_bullets(public_info)}\n\n"
        "Your individual information:\n"
        f"{_as_bullets(private_info)}\n\n"

    "Discussion instructions:\n"
    "Discuss the candidates naturally with the other group members.\n"
    f"{information_sharing_guidance}\n"
    "Share information from your own candidate materials when it is relevant for judging a candidate's suitability.\n"
    "Prefer sharing important private facts that have not yet appeared in the discussion over repeating facts already known to the group.\n"
    "Take into account information contributed by others.\n"
    "Do not assume your own information alone is complete.\n"
    "Do not treat an early majority preference as a final decision until the group has had a chance to discuss information about the candidates.\n"
    "Your aim is not to defend your initial preference.\n"
    "Your aim is to identify the candidate who is best suited for the long-distance pilot position based on all information available to the group.\n\n"

    f"{transparency_section}\n\n"

    "Grounding rule:\n"
    f"Use only candidate attributes explicitly present in your {_grounding_sources()}.\n"
    "Do not invent candidate attributes, background details, aviation procedures, training plans, technologies, mitigation strategies, or explanations not explicitly given in the task.\n"
    "If a drawback is present, treat it as evidence to weigh, not as something you may solve by inventing a remedy.\n\n"

    f"You may ask other agents specific questions as tools: {', '.join(other_agent_tools)}.\n"
    "Use tool calls to gather candidate information that may be distributed across group members.\n"
    "Your own information is incomplete, so missing evidence in your own materials does not mean the candidate lacks that quality.\n"
    "If one agent does not have information about a candidate or criterion, this also does not mean the candidate lacks that quality; another agent may have relevant information.\n"
    "Ask targeted questions about specific candidates, criteria, strengths, drawbacks, or unresolved comparisons, while respecting the active context transparency policy.\n"
    "Do not use tool calls to systematically reconstruct every agent's full information sheet.\n"
    "Do not ask for another agent's full information sheet or ask which candidate is correct.\n"
    "A tool call is only an information-gathering step.\n"
    "After any tool answer, you must still produce your scheduled public contribution using exactly "
    f"{PUBLIC_MESSAGE_LABEL} "
    f"and {METADATA_JSON_LABEL}.\n\n"

    "Internal Memory:\n"
    f"{memory_context}"
    f"{memory_guided_turn}"

    "Discussion so far:\n"
    f"{discussion_history}\n\n"

    "Discussion progression:\n"
    "Use the discussion to exchange relevant information and work toward a shared final recommendation, while staying within the active context transparency policy.\n"
    "Start with a provisional assessment, but remain open to changing your position when other agents contribute relevant evidence.\n"
    "Try to convince others when your information supports a candidate, and allow yourself to be convinced when the combined evidence supports a different candidate.\n"
    "Do not treat early agreement as final if important candidate information may still be missing.\n"
    "As the discussion develops, focus increasingly on resolving disagreements, comparing leading candidates, and identifying which candidate is best supported by the information shared by the group, without exceeding the disclosure level allowed by the active context transparency policy.\n"
    "Support a final unanimous decision only when the group has had a reasonable chance to exchange and consider relevant information.\n\n"

    "Output only the two sections below, with no planning notes and no text "
    f"before {PUBLIC_MESSAGE_LABEL}.\n\n"

    f"{PUBLIC_MESSAGE_LABEL}:\n"
    f"{public_message_template}\n\n"

    f"{METADATA_JSON_LABEL}:\n"
    f"{{\"agent\": \"{agent_key}\", \"vote\": \"<{vote_options}>\"}}\n"
)


def build_memory_update_instruction(
    agent_key: str,
    ctx=None,
    latest_speaker_key: str | None = None,
) -> str:
    """Build the prompt for a passive memory update after a contribution."""
    memory = read_agent_memory(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    latest_speaker = latest_speaker_key or "unknown_agent"
    latest_vote = _latest_vote_for_agent(ctx, latest_speaker_key)
    latest_speaker_role = (
        "This agent was the latest scheduled speaker."
        if latest_speaker_key == agent_key
        else "Another agent was the latest scheduled speaker."
    )

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"
        "You are maintaining private notes during a group discussion by an airline "
        "personnel selection committee. The airline is hiring a new pilot for "
        "long-distance flights. Your group must choose one candidate.\n\n"

        "Task:\n"
        f"{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        "Information structure:\n"
        "You have received individual information about the candidates. Part of the "
        "information available to group members is identical, and part of it "
        "differs across group members. On the basis of the full information set held "
        "within the group, one candidate is clearly the best choice. Your group's task "
        "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

        "Latest scheduled speaker context:\n"
        f"- Latest scheduled speaker: {latest_speaker}\n"
        f"- Latest speaker vote: {latest_vote}\n"
        f"- Relationship to this memory: {latest_speaker_role}\n\n"

        "Previous internal memory:\n"
        f"{memory}\n\n"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Update your private notes for use in later discussion turns. Preserve your "
        "own current position unless your own latest contribution changed it. Record "
        "important candidate information that has been mentioned in discussion, who "
        "supports which candidate, open questions, and the next steps.\n\n"

        "When summarizing role fit, map explicit facts to the stated selection "
        "criteria by ordinary meaning rather than exact wording. Do not say a "
        "candidate lacks evidence for a criterion when a stated fact reasonably "
        "supports that criterion.\n\n"

        "Do not add facts that were not in the discussion. If another "
        "agent states a candidate fact, record it as information reported by that "
        "agent unless it is also present in your own materials. Do not invent or "
        "infer additional candidate attributes.\n\n"

        "Preference ownership rules:\n"
        "If the latest scheduled speaker is this same agent, update 'My Last Vote' "
        "from the latest speaker vote and update 'My Current Working Favorite' to "
        "match this agent's latest stated position. If the latest scheduled speaker "
        "is another agent, do not change 'My Last Vote' or 'My Current Working "
        "Favorite' solely because that agent recommended a candidate. Instead, record "
        "that agent's vote under 'Other Agents' Positions' and record any evidence "
        "they contributed under the relevant candidate.\n\n"

        "Keep the memory compact. Do not include a transcript. Do not include round "
        "labels. Return only a JSON object matching the configured schema. Each "
        "JSON value must contain the complete markdown body for that memory section, "
        "without the section heading. Use these keys: task_summary, "
        "candidate_summary_table, my_position, other_agents_positions, "
        "emerging_group_view, open_questions, and next_step_focus. Do not call "
        "tools, do not wrap the JSON or markdown in a code fence, and do not add a "
        "public discussion contribution."
    )

def build_agent_tool_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the prompt for an agent answering another agent through a tool call."""
    memory_context = _memory_context_section(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    transparency_section = _transparency_section("tool")

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"
        "You are a member of the personnel selection committee of an airline company. "
        "The airline is hiring a new pilot for long-distance flights. Another group "
        "member has asked you a question during the discussion.\n\n"

        "Task:\n"
        f"{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        "Information structure:\n"
        "You have received individual information about the candidates. Part of the "
        "information available to group members is identical, and part of it "
        "differs across group members. On the basis of the full information set held "
        "within the group, one candidate is clearly the best choice. Your group's task "
        "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

        "Public information known to all agents:\n"
        f"{_as_bullets(public_info)}\n\n"
        "Your individual information:\n"
        f"{_as_bullets(private_info)}\n\n"

        f"Answer only using facts explicitly present in your {_grounding_sources()}. "
        "Answer the other group member's question directly, as you would during "
        "the group discussion. Reveal relevant candidate information you hold that answers the question, "
        "while staying at the detail level allowed by the active context transparency policy. "
        "If the question asks about a selection criterion, include explicit candidate "
        "facts you have that seem relevant to that criterion, without inventing "
        "candidate attributes or background details. "
        "If the question asks for information you do not have, say that you do not have that "
        "information.\n\n"

        f"{transparency_section}\n\n"

        "Internal Memory:\n"
        f"{memory_context}"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Output only the direct answer. Do not include metadata, planning notes, or "
        "special formatting. Do not update your private notes during this response."
    )