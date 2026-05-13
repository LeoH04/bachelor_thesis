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
            "Share at most one fact or concern. Do not explain your reasoning."
        ),
        "tool": (
            "Answer with one brief, relevant fact. Do not elaborate."
        ),
    },
    "moderate": {
        "discussion": (
            "Share one or two relevant facts or concerns. You don't need to reveal "
            "everything at once — share what seems most useful right now and explain your reasoning."
        ),
        "tool": (
            "Answer directly with the most relevant fact or facts you have."
        ),
    },
    "high": {
        "discussion": (
            "Share your reasoning openly: what you know, what others have contributed, "
            "your current assessment, and what would change your view."
        ),
        "tool": (
            "Answer directly. Mention uncertainty if relevant and briefly explain "
            "how the information bears on the candidate comparison."
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


def _selection_criteria_section() -> str:
    return (
        "Selection criteria:\n"
        "Evaluate candidates holistically for a long-distance pilot role:\n"
        "- Reliability and responsibility\n"
        "- Technical and cognitive competence\n"
        "- Calmness, judgment, and performance under pressure\n"
        "- Sound and timely decision-making\n"
        "- Teamwork, communication, and crew cooperation\n"
        "- Professional development and long-term suitability\n\n"
        "Weigh strengths and weaknesses by how serious they are for safe "
        "long-distance flight operations. Do not decide on one standout "
        "strength or weakness alone.\n\n"
    )


def _transparency_section(kind: str) -> str:
    """Build the condition-specific communication instruction section."""
    condition = _context_transparency_condition()
    policy = TRANSPARENCY_POLICIES[condition][kind]
    return (
        "Communication rules:\n"
        f"{policy}\n\n"
    )


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
    memory_context = _memory_context_section(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK["public_information"]
    private_info = TASK["private_information"][agent_key]
    candidates = TASK["candidates"]
    goal = TASK["goal"]
    current_round = _round_number()
    other_agents = [key for key in AGENT_KEYS if key != agent_key]
    other_agent_tools = [
        f"{key}_tool ({key.replace('_', ' ').title()})"
        for key in other_agents
    ]
    vote_options = "|".join(candidates)

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"

        "You are a member of an airline personnel selection committee. "
        "The airline is hiring a pilot for long-distance flights. "
        "The group must choose one candidate.\n\n"

        "Task:\n"
        f"{goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Current discussion round: {current_round}\n\n"

        f"{_selection_criteria_section()}"

        "Information structure:\n"
        "You each hold a different subset of candidate information. "
        "No single agent has the full picture. "
        "The group can only identify the best candidate by combining "
        "what each of you knows through discussion.\n\n"

        "Information available to you:\n"
        f"{_as_bullets(public_info + private_info)}\n\n"

        f"{memory_context}\n\n"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Grounding rule:\n"
        f"Use only candidate attributes explicitly present in your "
        f"{_grounding_sources()}. Do not invent attributes, explanations, "
        "or mitigation strategies. If a weakness is present, weigh it as "
        "evidence rather than reasoning it away.\n\n"

        "Discussion behavior:\n"
        "Your information is incomplete. Others may know things you don't — "
        "including facts that would change your current assessment. "
        "Don't treat early consensus as final. A wrong answer is worse "
        "than a longer discussion.\n\n"

        "When reading the discussion history, if you see a question another "
        "agent asked that you can answer from your own information, include "
        "that answer in your public contribution — even if you were not "
        "directly asked.\n\n"

        "When you find yourself leaning toward a candidate, actively look for "
        "reasons you might be wrong. Ask other agents what they know about the "
        "strengths of candidates you have less information on.\n\n"

        f"You may ask other agents targeted questions using these tools: "
        f"{', '.join(other_agent_tools)}. "
        "A tool call is only an information-gathering step — after any tool "
        "answer, continue your turn and produce your public contribution.\n\n"

        "When using tools, ask about candidate strengths and attributes you "
        "don't have. Do not ask whether weaknesses have caused incidents. "
        "Incident reports are not available; only candidate attributes are. "
        "If one agent does not have the answer, the other agent might. "
        "A 'I don't have that information' response means that agent lacks it — "
        "not that the information doesn't exist.\n\n"

        "Before settling on a preference, make sure you have considered every "
        "candidate. Do not drop a candidate from consideration until you have "
        "checked whether others hold positive information about them that you "
        "are missing.\n\n"

        f"{_transparency_section('discussion')}\n\n"

        "Output only the two sections below. Do not include planning notes "
        "or extra text.\n\n"

        f"{PUBLIC_MESSAGE_LABEL}:\n"
        "<your contribution to the discussion>\n\n"

        f"{METADATA_JSON_LABEL}:\n"
        f"{{\"agent\": \"{agent_key}\", \"vote\": \"<{vote_options}>\"}}\n"
    )


def build_memory_update_instruction(
    agent_key: str,
    ctx=None,
    latest_speaker_key: str | None = None,
) -> str:
    memory = read_agent_memory(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK["public_information"]
    private_info = TASK["private_information"][agent_key]
    candidates = TASK["candidates"]
    goal = TASK["goal"]
    latest_speaker = latest_speaker_key or "unknown_agent"
    latest_vote = _latest_vote_for_agent(ctx, latest_speaker_key)
    latest_speaker_role = (
        "This agent was the latest scheduled speaker."
        if latest_speaker_key == agent_key
        else "Another agent was the latest scheduled speaker."
    )

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"

        "You are maintaining private notes during a group discussion by an "
        "airline personnel selection committee choosing a long-distance pilot.\n\n"

        "Task:\n"
        f"{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        f"{_selection_criteria_section()}"

        "Information available to you:\n"
        f"{_as_bullets(public_info + private_info)}\n\n"

        "Latest scheduled speaker context:\n"
        f"- Latest scheduled speaker: {latest_speaker}\n"
        f"- Latest speaker vote: {latest_vote}\n"
        f"- Relationship to this memory: {latest_speaker_role}\n\n"

        "Previous internal memory:\n"
        f"{memory}\n\n"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Update your private notes. Record important candidate information "
        "from the discussion, who supports which candidate, major disagreements, "
        "and what is still blocking a unanimous decision.\n\n"

        "Distinguish between isolated weaknesses and repeated or "
        "safety-relevant ones. Do not add facts not present in your "
        "information or the discussion. If another agent states a candidate "
        "fact, record it as reported by that agent unless it also appears "
        "in your own materials.\n\n"

        "Memory output rules:\n"
        "Return a JSON object matching the configured schema. Each value must "
        "contain only the markdown body for that section, without section "
        "headings or HTML markers. Use exactly these keys:\n"
        "- task_summary\n"
        "- revealed_facts_by_source\n"
        "- candidate_evaluation\n"
        "- my_position\n"
        "- other_agents_positions\n"
        "- emerging_group_view\n"
        "- open_questions_next_step_focus\n\n"

        "Preference ownership rules:\n"
        "If the latest speaker is this agent, update 'My Last Vote' and "
        "'My Current Working Favorite' from that vote. If the latest speaker "
        "is another agent, do not change 'My Last Vote' or 'My Current "
        "Working Favorite' — record their vote under 'Other Agents' Positions' "
        "only.\n\n"

        "Output only the structured JSON object. "
        "Do not call tools, do not wrap in a code fence, do not add a "
        "public discussion contribution."
    )


def build_agent_tool_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    memory_context = _memory_context_section(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK["public_information"]
    private_info = TASK["private_information"][agent_key]
    candidates = TASK["candidates"]
    goal = TASK["goal"]

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"

        "Another committee member has asked you a question during the "
        "pilot-selection discussion. Your role is to answer from your own "
        "available candidate information.\n\n"

        "Task:\n"
        f"{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        f"{_selection_criteria_section()}"

        "Information available to you:\n"
        f"{_as_bullets(public_info + private_info)}\n\n"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        f"{memory_context}\n\n"

        "Grounding rule:\n"
        f"Answer only using facts explicitly present in your "
        f"{_grounding_sources()}. "
        "Do not invent attributes, explanations, incidents, or mitigation "
        "strategies. If you do not have relevant information, say so.\n\n"

        f"{_transparency_section('tool')}\n\n"

        "Answer the question directly. Do not include metadata or "
        "planning notes."
    )
