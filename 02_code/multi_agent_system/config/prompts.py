"""Build prompts for discussion, memory update, and tool-response agents."""

from .history import _get_state, _round_number, build_public_discussion_history
from .memory import read_agent_memory
from .response_text import (
    METADATA_JSON_LABEL,
    PUBLIC_MESSAGE_LABEL,
    extract_vote_from_response,
)
from .task import AGENT_KEYS, TASK, _as_bullets


def _latest_vote_for_agent(ctx, agent_key: str | None) -> str:
    """Return the latest recorded vote for an agent, or a placeholder."""
    if not agent_key:
        return "Unavailable"

    response = _get_state(ctx).get(f"{agent_key}_response", "")
    return extract_vote_from_response(response) or "Unavailable"


def build_agent_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the full prompt for an agent's scheduled public discussion turn."""
    memory = read_agent_memory(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    current_round = _round_number()
    other_agents = [key for key in AGENT_KEYS if key != agent_key]
    vote_options = "|".join(candidates) if candidates else "candidate"

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
    "You have received individual information about the candidates.\n"
    "Part of the information available to group members may be identical.\n"
    "Part of the information may differ across group members.\n"
    "On the basis of the full information set held within the group, one candidate is clearly the best choice.\n"
    "The group's task is to find this candidate through discussion and reach a unanimous final decision.\n\n"

    "Information available to you:\n"
    f"{_as_bullets(public_info + private_info)}\n\n"

    "Discussion instructions:\n"
    "Discuss the candidates naturally with the other group members.\n"
    "Share information from your own candidate materials when it is relevant for judging a candidate's suitability.\n"
    "Take into account information contributed by others.\n"
    "Do not assume your own information alone is complete.\n"
    "Do not treat an early majority preference as a final decision until the group has had a chance to discuss information about the candidates.\n"
    "Your aim is not to defend your initial preference.\n"
    "Your aim is to identify the candidate who is best suited for the long-distance pilot position based on all information available to the group.\n\n"

    "Grounding rule:\n"
    "Use only candidate attributes explicitly present in your candidate information, previous internal memory, or the discussion so far.\n"
    "Do not invent candidate attributes, background details, aviation procedures, training plans, technologies, mitigation strategies, or explanations not explicitly given in the task.\n"
    "If a drawback is present, treat it as evidence to weigh, not as something you may solve by inventing a remedy.\n\n"

    f"You may ask other agents specific questions as tools: {', '.join(other_agents)}.\n"
    "A tool call is only an information-gathering step.\n"
    "After any tool answer, you must still produce your scheduled public contribution using exactly "
    f"{PUBLIC_MESSAGE_LABEL} "
    f"and {METADATA_JSON_LABEL}.\n\n"

    "Previous internal memory:\n"
    f"{memory}\n\n"

    "Discussion so far:\n"
    f"{discussion_history}\n\n"

    "Round guidance:\n"
    "Round 1: State a provisional preference, not a final decision.\n"
    "Round 1: Share one or two important pieces of candidate information that you think the group should consider, especially information not yet mentioned.\n"
    "Round 1: Do not claim that the group is ready for a unanimous final decision unless meaningful information about the candidates has been discussed.\n"
    "Round 2 and later: Compare your current preference with the strongest evidence shared by others.\n"
    "Round 2 and later: Update your position if the combined evidence supports a different candidate.\n"
    "Final decision: Support a unanimous decision only when the group has considered the relevant information shared across members.\n\n"

    "Output only the two sections below, with no planning notes and no text "
    f"before {PUBLIC_MESSAGE_LABEL}.\n\n"

    f"{PUBLIC_MESSAGE_LABEL}:\n"
    "<your public contribution: state your current provisional preference; "
    "share one or two important pieces of candidate information that you think the group should consider, especially information not yet mentioned; "
    "respond to important information raised by others; "
    "and state what comparison still seems important before a final unanimous decision>\n\n"

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
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
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
        "information available to group members may be identical, and part of it may "
        "differ across group members. On the basis of the full information set held "
        "within the group, one candidate is clearly the best choice. The group's task "
        "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

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

        "Update your private notes for use in later discussion turns. Preserve your "
        "own current position unless your own latest contribution changed it. Record "
        "important candidate information that has been mentioned in discussion, who "
        "supports which candidate, major disagreements, and any issues still blocking "
        "a unanimous decision.\n\n"

        "Do not copy your full candidate-information sheet into memory. Do not add "
        "facts that were not in your information or in the discussion. If another "
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
        "labels. Output only the complete updated Shared Mental Model markdown. "
        "Do not call tools, do not wrap the markdown in a code fence, and do not "
        "add a public discussion contribution."
    )

def build_agent_tool_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the prompt for an agent answering another agent through a tool call."""
    memory = read_agent_memory(agent_key)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

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
        "information available to group members may be identical, and part of it may "
        "differ across group members. On the basis of the full information set held "
        "within the group, one candidate is clearly the best choice. The group's task "
        "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

        "Information available to you:\n"
        f"{_as_bullets(public_info + private_info)}\n\n"

        "Grounding rule:\n"
        "Answer only using facts explicitly present in your candidate information, "
        "previous internal memory, or the discussion so far. Do not invent candidate "
        "attributes or background details. If the question asks for information you "
        "do not have, say that you do not have that information.\n\n"

        "Previous internal memory:\n"
        f"{memory}\n\n"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Answer the other group member's question directly and briefly, as you would "
        "during the group discussion. Provide relevant candidate information you have, "
        "but do not update your private notes during this response.\n\n"

        "Output only the direct answer. Do not include metadata, planning notes, or "
        "special formatting."
    )
