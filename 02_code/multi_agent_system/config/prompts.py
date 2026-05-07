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
            "LOW context transparency means you expose mainly conclusions or "
            "isolated signals from your internal decision context.\n"
            "Public contribution rules:\n"
            "- State your current position or recommendation.\n"
            "- Share at most one brief supporting signal, fact, or concern.\n"
            "- Use minimal explanation.\n"
            "- Do not use an explicit reasoning structure.\n"
            "- Do not provide source/provenance labels.\n"
            "- Do not provide confidence estimates.\n"
            "- Do not discuss detailed alternatives or comparisons.\n"
            "- Do not explicitly reference prior shared context unless necessary "
            "to answer a direct question.\n"
            "Hidden-profile instantiation: state your preferred candidate and "
            "one short candidate fact or concern, with no detailed comparison."
        ),
        "tool": (
            "LOW context transparency means your public tool answer should expose "
            "only the minimum useful context.\n"
            "Answer with at most one brief fact, concern, or direct statement. "
            "Do not add reasoning structure, source/provenance labels, confidence, "
            "or detailed comparisons."
        ),
        "public_template": (
            "<state your current preferred candidate and at most one brief "
            "candidate fact or concern; keep the contribution sparse and do not "
            "include detailed reasoning, comparison, confidence, sources, or "
            "prior-discussion references>"
        ),
    },
    "moderate": {
        "discussion": (
            "MODERATE context transparency means you expose a compact, "
            "task-relevant version of your internal decision context.\n"
            "Public contribution rules:\n"
            "- State your current position or recommendation.\n"
            "- Share one or two key reasons behind that position.\n"
            "- Link each reason to the relevant candidate or alternative.\n"
            "- Briefly evaluate why the reasons matter for the task goal.\n"
            "- Include one main tradeoff, uncertainty, or decision blocker.\n"
            "- Reference shared context only when it is useful for coordination.\n"
            "- Do not provide exhaustive evidence lists, source-heavy reasoning, "
            "or long recaps.\n"
            "Hidden-profile instantiation: state your preferred candidate, give "
            "one or two candidate-linked facts, explain briefly why they matter "
            "for the pilot role, and name one comparison or unresolved issue."
        ),
        "tool": (
            "MODERATE context transparency means your public tool answer should "
            "provide compact, task-relevant context.\n"
            "Answer directly with one or two relevant facts or concerns. Link "
            "them to the candidate or alternative they affect, and include a short "
            "evaluation only if it helps the caller use the information."
        ),
        "public_template": (
            "<state your current preferred candidate; give one or two "
            "candidate-linked reasons; briefly explain why they matter for the "
            "role; include one main tradeoff, uncertainty, or unresolved issue; "
            "avoid exhaustive reasoning summaries>"
        ),
    },
    "high": {
        "discussion": (
            "HIGH context transparency means you expose an expanded public "
            "reasoning-context summary of your internal decision context.\n"
            "Public contribution rules:\n"
            "- State your current position or recommendation.\n"
            "- Include confidence or uncertainty.\n"
            "- Link evidence to candidates or alternatives.\n"
            "- Distinguish your own information from information shared by others.\n"
            "- Reference relevant prior shared context.\n"
            "- Compare major alternatives and tradeoffs.\n"
            "- State assumptions and unresolved uncertainties when relevant.\n"
            "- State what would change your decision.\n"
            "- Do not expose raw hidden chain-of-thought. Provide only a concise, "
            "structured public reasoning summary.\n"
            "Hidden-profile instantiation: include the required Reasoning summary "
            "with Key evidence used, Evidence from others, Alternatives considered, "
            "Main tradeoff, Remaining uncertainty, and What would change my vote."
        ),
        "tool": (
            "HIGH context transparency means your public tool answer should expose "
            "a concise reasoning-context summary, not raw hidden chain-of-thought.\n"
            "Answer directly, identify whether the information comes from your own "
            "materials or the prior discussion, mention uncertainty if relevant, "
            "and briefly explain how the answer affects the decision context."
        ),
        "public_template": (
            "Use this structure:\n"
            "Current position: <preferred candidate>\n"
            "Confidence/uncertainty: <brief estimate or qualitative uncertainty>\n"
            "Reasoning summary:\n"
            "- Key evidence used: <own/public evidence supporting the position>\n"
            "- Evidence from others: <relevant information shared by other agents>\n"
            "- Alternatives considered: <major alternatives and why they are weaker or still plausible>\n"
            "- Main tradeoff: <central decision tradeoff>\n"
            "- Remaining uncertainty: <main open issue>\n"
            "- What would change my vote: <specific evidence or comparison that could change the position>"
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
        f"Active condition: {condition}\n"
        f"{policy}"
    )


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
    vote_options = "|".join(candidates) if candidates else "candidate"
    transparency_section = _transparency_section("discussion")
    public_message_template = _public_message_template()

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
    "Prefer sharing important private facts that have not yet appeared in the discussion over repeating facts already known to the group.\n"
    "Take into account information contributed by others.\n"
    "Do not assume your own information alone is complete.\n"
    "Evaluate the role criteria by ordinary meaning, not only by exact keywords: conscientiousness and taking responsibility support reliability; handling stress, staying calm, and responding to unexpected events support calmness under pressure; creating a positive crew atmosphere, concern for others, and leadership support cooperation; technical understanding, attention, weather assessment, computer skills, spatial vision, and problem solving support technical competence.\n"
    "A candidate with balanced evidence across the essential criteria may be better than a candidate with one very strong trait but repeated cooperation drawbacks.\n"
    "Cooperation is safety-critical for cockpit work: repeated direct cooperation negatives such as being uncooperative, making nasty remarks, using the wrong tone, being pretentious, having a hot temper, being a loner, being unfriendly, or rejecting others' ideas must be weighed heavily. Do not select a candidate mainly because of one exceptional strength if that candidate's cooperation evidence is only negative.\n"
    "After all agents have contributed, actively look for the candidate whose combined shared evidence covers reliability, technical competence, calmness under pressure, cooperation, and high-responsibility suitability most evenly.\n"
    "Do not treat an early majority preference as a final decision until the group has had a chance to discuss information about the candidates.\n"
    "Your aim is not to defend your initial preference.\n"
    "Your aim is to identify the candidate who is best suited for the long-distance pilot position based on all information available to the group.\n\n"

    f"{transparency_section}\n\n"

    "Grounding rule:\n"
    f"Use only candidate attributes explicitly present in your {_grounding_sources()}.\n"
    "Do not invent candidate attributes, background details, aviation procedures, training plans, technologies, mitigation strategies, or explanations not explicitly given in the task.\n"
    "If a drawback is present, treat it as evidence to weigh, not as something you may solve by inventing a remedy.\n\n"

    f"You may ask other agents specific questions as tools: {', '.join(other_agents)}.\n"
    "A tool call is only an information-gathering step.\n"
    "After any tool answer, you must still produce your scheduled public contribution using exactly "
    f"{PUBLIC_MESSAGE_LABEL} "
    f"and {METADATA_JSON_LABEL}.\n\n"

    f"{memory_context}"

    "Discussion so far:\n"
    f"{discussion_history}\n\n"

    "Round behavior:\n"
    "Round 1: State a provisional preference, not a final decision.\n"
    "Round 1: Contribute information only at the detail level allowed by the active context transparency policy.\n"
    "Round 1: Do not claim that the group is ready for a unanimous final decision unless meaningful information about the candidates has been discussed.\n"
    "Round 2 and later: Take into account newly shared information while staying within the active context transparency policy.\n"
    "Round 2 and later: Update your position if the combined evidence supports a different candidate.\n"
    "Final decision: Support a unanimous decision only when the group has considered the relevant information shared across members.\n\n"

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

        "When summarizing role fit, map explicit facts to the role criteria by "
        "ordinary meaning rather than exact wording. Do not say a candidate lacks "
        "evidence for reliability, calmness, cooperation, or technical competence "
        "when a stated fact reasonably supports that criterion. Treat repeated "
        "direct cooperation negatives as safety-relevant drawbacks, not minor "
        "personality details.\n\n"

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
        "information available to group members may be identical, and part of it may "
        "differ across group members. On the basis of the full information set held "
        "within the group, one candidate is clearly the best choice. The group's task "
        "is to find this candidate through discussion and reach a unanimous final decision.\n\n"

        "Information available to you:\n"
        f"{_as_bullets(public_info + private_info)}\n\n"

        "Grounding rule:\n"
        f"Answer only using facts explicitly present in your {_grounding_sources()}. "
        "Do not invent candidate attributes or background details. If the question "
        "asks for information you do not have, say that you do not have that "
        "information.\n\n"

        f"{transparency_section}\n\n"

        f"{memory_context}"

        "Discussion so far:\n"
        f"{discussion_history}\n\n"

        "Answer the other group member's question directly, as you would during "
        "the group discussion. Provide relevant candidate information you have "
        "only at the detail level allowed by the active context transparency "
        "policy. If the question asks about a role criterion, include explicit "
        "facts that bear on that criterion even when they use different wording. "
        "Do not update your private notes during this response.\n\n"

        "Output only the direct answer. Do not include metadata, planning notes, or "
        "special formatting."
    )
