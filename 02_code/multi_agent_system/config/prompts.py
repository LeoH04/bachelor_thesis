"""
Prompt builders for the airline HR hidden-profile hiring simulation.

Core idea:
- Baseline condition: agents discuss as a professional HR hiring panel and
  track the meeting from the raw public discussion history.
- Treatment condition: agents discuss under the same role, task, criteria,
  facts, and meeting rules, but additionally maintain an explicit structured
  shared mental model of the evolving team knowledge state.

The prompt is intentionally written as a realistic hiring-panel scenario,
not as an experiment. Agents are HR professionals at a fictional airline who
have interviewed the candidates and now meet to agree on one hiring
recommendation for a long-distance pilot position.
"""

from .context_transparency import (
    context_transparency_condition,
    input_history_scope,
    thought_history_enabled,
)
from .history import _get_state, _round_number, build_public_discussion_history
from .memory import read_agent_memory
from .response_text import (
    METADATA_JSON_LABEL,
    PUBLIC_MESSAGE_LABEL,
    extract_vote_from_response,
)
from .smm import explicit_smm_memory_enabled
from .task import AGENT_KEYS, TASK, _as_bullets


# ---------------------------------------------------------------------------
# Realistic setting
# ---------------------------------------------------------------------------

AIRLINE_NAME = "AeroConnect Airlines"

AGENT_PERSONAS = {
    "agent_1": {
        "name": "Anna Keller",
        "role": "HR Selection Specialist for Flight Operations",
    },
    "agent_2": {
        "name": "Markus Weber",
        "role": "Pilot Assessment Specialist",
    },
    "agent_3": {
        "name": "Sofia Brandt",
        "role": "Recruiting Specialist for Cockpit Personnel",
    },
    "agent_4": {
        "name": "Daniel Hoffmann",
        "role": "HR Assessment Specialist for Flight Operations",
    },
}


def _agent_persona(agent_key: str) -> dict:
    """Return a realistic persona for the given agent key."""
    return AGENT_PERSONAS.get(
        agent_key,
        {
            "name": agent_key.replace("_", " ").title(),
            "role": "HR Selection Panel Member",
        },
    )


def _agent_display_name(agent_key: str) -> str:
    """Return the human-readable name and role for an agent."""
    persona = _agent_persona(agent_key)
    return f"{persona['name']}, {persona['role']}"


# ---------------------------------------------------------------------------
# Input context transparency
# ---------------------------------------------------------------------------

PUBLIC_MESSAGE_TEMPLATE = (
    "<concise professional meeting contribution: current recommendation, useful "
    "candidate evidence, comparison, uncertainty, or next decision focus>"
)


def _public_message_template() -> str:
    """Return the shared public-message template for all transparency conditions."""
    return PUBLIC_MESSAGE_TEMPLATE


def _input_context_section() -> str:
    """Describe the input context available under the active condition."""
    condition = context_transparency_condition()
    scope = input_history_scope()

    if condition == "low":
        detail = (
            "For this turn, the meeting discussion below contains only public "
            "messages and tool exchanges from the current discussion round. "
            "Earlier rounds are not included in the visible meeting history."
        )
    elif condition == "high":
        detail = (
            "For this turn, the meeting discussion below contains the full public "
            "discussion and tool-exchange history. When available, it also includes "
            "stored model thoughts that were attached to earlier model responses. "
            "Treat those thoughts as context for understanding prior discussion "
            "state, not as new candidate evidence."
        )
    else:
        detail = (
            "For this turn, the meeting discussion below contains the full public "
            "discussion and tool-exchange history. It does not include stored "
            "model thoughts."
        )

    return (
        "Input context available in this turn:\n"
        f"Condition: {condition}; visible discussion scope: {scope}; "
        f"model thoughts included: {thought_history_enabled()}.\n"
        f"{detail}\n\n"
    )


def _shared_communication_guidance_section() -> str:
    """Return condition-neutral public communication guidance."""
    return (
        "Communication behavior:\n"
        "Discuss naturally as a professional HR panel member. Share the candidate "
        "facts, comparisons, concerns, tradeoffs, or uncertainties that are most "
        "useful for the current step of the meeting. You may compare candidates, "
        "ask targeted tool questions, update your position, or try to persuade "
        "colleagues, while remaining concise and evidence-based.\n\n"
    )


# ---------------------------------------------------------------------------
# Shared decision criteria and professional behavior
# ---------------------------------------------------------------------------

def _selection_criteria_section() -> str:
    """Return the shared pilot hiring criteria."""
    return (
        "Pilot selection criteria:\n"
        "Evaluate the candidates for a long-distance pilot position using these "
        "role-relevant criteria:\n"
        "- Operational reliability: dependable, conscientious, and consistent behavior\n"
        "- Stress resilience: calm and effective performance under pressure or in crisis situations\n"
        "- Technical and cognitive competence: ability to understand complex systems and handle demanding operational tasks\n"
        "- Decision quality: correct and timely decisions in safety-relevant situations\n"
        "- Attention and information accuracy: concentration and accurate handling of operationally relevant details\n"
        "- Crew cooperation: constructive collaboration and contribution to a positive cockpit or team environment\n"
        "- Professional communication: respectful and appropriate communication with colleagues\n"
        "- Responsibility and role maturity: judgment suitable for high-risk international flights\n"
        "- Adaptability and feedback orientation: openness to criticism, new ideas, and further development\n\n"
        "Decision principle:\n"
        "Recommend the candidate with the strongest overall fit for the pilot role. "
        "Do not overvalue one impressive strength while ignoring serious concerns "
        "on other safety-relevant criteria. At the same time, do not reject a "
        "candidate because one source lacks information about them on a criterion. "
        "Use the panel discussion to combine distributed observations before "
        "settling on a recommendation.\n\n"
    )


def _professional_hr_behavior_section() -> str:
    """Return general professional behavior instructions."""
    return (
        "Professional HR panel behavior:\n"
        "You are not playing a game and you are not trying to win an argument. "
        "You are part of a serious HR selection panel making a safety-critical "
        "hiring recommendation for an airline.\n\n"
        "Behave like a professional interviewer in a real selection meeting:\n"
        "- be concise, respectful, and evidence-based,\n"
        "- take colleagues' observations seriously,\n"
        "- separate candidate evidence from speculation,\n"
        "- do not overstate weak evidence,\n"
        "- do not ignore concerns because you personally prefer a candidate,\n"
        "- compare candidates against the pilot selection criteria,\n"
        "- revise your recommendation when the combined evidence supports it,\n"
        "- work toward a justified team recommendation, not a quick agreement.\n\n"
    )


def _meeting_process_section() -> str:
    """Return condition-neutral meeting process rules."""
    return (
        "Meeting process:\n"
        "This is a live HR selection meeting, not a written evidence inventory. "
        "Do not dump all interview notes at once. In each scheduled turn, make "
        "the single most useful contribution for moving the panel toward a "
        "well-grounded hiring recommendation.\n\n"
        "A useful contribution is usually one of the following:\n"
        "- share one or two relevant candidate observations,\n"
        "- compare candidates on one important hiring criterion,\n"
        "- explain why new information supports or changes your recommendation,\n"
        "- point out one unresolved issue that matters for the decision,\n"
        "- or ask a targeted question via an available agent tool before speaking publicly.\n\n"
        "Before asking for external records, simulator debriefs, references, or "
        "other outside data, first disclose any relevant candidate information "
        "available to you and use agent tools to check whether another panel "
        "member has internal interview or assessment observations on the issue.\n\n"

        "Candidate review process:\n"
        "Across the meeting, help the panel review all candidates in an organized "
        "way. The panel should not jump to final consensus only because one "
        "candidate looks attractive early.\n\n"
        "For each candidate, the panel should try to establish:\n"
        "- the strongest evidence in favor of the candidate,\n"
        "- the most important concern or limitation,\n"
        "- which pilot selection criteria the candidate clearly satisfies,\n"
        "- which criteria remain uncertain or contested,\n"
        "- and how the candidate compares with the strongest evidence-based alternative.\n\n"
        "You do not need to cover all candidates or all criteria in one turn. "
        "Contribute only the next useful piece of the comparison. If an important "
        "comparison cannot be made because information is missing, ask a targeted "
        "question using an available agent tool before writing your public message.\n\n"

        "Recommendation behavior:\n"
        "Your vote is your current provisional recommendation, not a final "
        "commitment and not a position to defend at all costs. Update it when "
        "the combined panel evidence supports a different candidate. Do not "
        "change your vote merely to match an emerging majority. Do not treat "
        "early agreement as final if important candidates, criteria, or unresolved "
        "issues have not yet been discussed.\n\n"
        "Readiness check before convergence:\n"
        "Before treating a consensus as well-grounded, check whether every "
        "candidate has been compared on the core pilot criteria using available "
        "panel evidence. If a criterion is still unclear, first disclose your "
        "own relevant information or ask a panel member for their internal observations. Do "
        "not delay the decision only for external data that is not present in "
        "the candidate information available in the meeting, public discussion, "
        "or tool answers.\n\n"
    )


def _round_guidance_section() -> str:
    """Return light guidance based on the current discussion round."""
    current_round = _round_number()

    if current_round <= 1:
        return (
            "Current meeting phase:\n"
            "This is the opening phase of the discussion. Start building a "
            "shared view of the candidates. Give an initial recommendation, but "
            "do not present it as final. Bring in one useful observation or "
            "comparison and leave room for colleagues' information to change "
            "the evaluation.\n\n"
        )

    if current_round == 2:
        return (
            "Current meeting phase:\n"
            "The panel should now compare candidates more directly and fill "
            "important information gaps. Focus on under-discussed candidates, "
            "unclear criteria, or comparisons between the current leading "
            "candidate and the strongest alternative.\n\n"
        )

    return (
        "Current meeting phase:\n"
        "The panel may move toward convergence only if the main candidates and "
        "decision-relevant criteria have been seriously considered. If a major "
        "gap remains, address it or ask a targeted tool question before simply "
        "agreeing with the current leading recommendation.\n\n"
    )


# ---------------------------------------------------------------------------
# Evidence boundaries and tool-question behavior
# ---------------------------------------------------------------------------

def _grounding_sources() -> str:
    """Return the evidence sources agents may use."""
    return (
        "the candidate information available to you and information explicitly "
        "shared in the meeting discussion"
    )


def _evidence_boundaries_section() -> str:
    """Return strict grounding instructions."""
    return (
        "Evidence boundaries:\n"
        f"Use only candidate attributes explicitly present in {_grounding_sources()}. "
        "Do not invent candidate traits, background details, aviation experience, "
        "training plans, incident reports, simulator results, technologies, risk "
        "mitigations, or explanations not explicitly given.\n\n"
        "If the meeting history includes model thoughts, treat them only as "
        "context about prior model state. Do not treat a model thought as a new "
        "candidate fact unless the same fact is also present in the candidate "
        "dossier, your own notes, a public message, or a public tool answer.\n\n"
        "If information is absent from your own notes, do not assume the candidate "
        "lacks that trait. Another interviewer may have elicited relevant "
        "information. If a colleague says they do not have information on a topic, "
        "that means only that this colleague personally does not have it.\n\n"
        "The panel should make the recommendation from candidate information "
        "available in the meeting, public discussion, and public tool answers. "
        "Do not keep asking for external records or future checks until available "
        "internal panel evidence has been shared or queried.\n\n"
    )


def _tool_question_section(agent_key: str) -> str:
    """Return instructions for asking other agents via tools."""
    other_agents = [key for key in AGENT_KEYS if key != agent_key]
    other_agent_tools = [
        f"{key}_tool ({_agent_display_name(key)})"
        for key in other_agents
    ]

    if not other_agent_tools:
        return (
            "Asking other panel members:\n"
            "No other interviewer tools are available in this run.\n\n"
        )

    return (
        "Asking other panel members:\n"
        f"You may direct specific questions to: {', '.join(other_agent_tools)}.\n\n"
        "If you need information from another panel member, you must ask using "
        "the available agent tool before writing your PUBLIC_MESSAGE. Do not "
        "write unanswered questions to other panel members inside PUBLIC_MESSAGE. "
        "Public questions are not answered unless they are made through a tool call.\n\n"
        "Ask targeted questions about specific candidates, criteria, strengths, "
        "concerns, or comparisons. Do not ask for another panel member's full "
        "notes and do not ask which candidate is the correct answer.\n\n"
        "Ask other panel members for internal interview or assessment observations "
        "before asking about external records, future reference checks, or "
        "simulator debriefs not already mentioned in the materials.\n\n"
        "Good tool questions sound like:\n"
        "- Did your interview notes include anything about Candidate C's reliability or technical competence?\n"
        "- Did Candidate B show anything relevant to crew cooperation or professional communication?\n"
        "- Is there anything you learned about Candidate D that should affect our long-distance pilot recommendation?\n\n"
        "After receiving a tool answer, use it in your public contribution if it "
        "is relevant. Your PUBLIC_MESSAGE may summarize the answer and explain "
        "how it affects your recommendation, but it must not contain unresolved "
        "questions directed at another panel member.\n\n"
    )


# ---------------------------------------------------------------------------
# Baseline vs treatment tracking
# ---------------------------------------------------------------------------

def _memory_block(agent_key: str) -> str:
    """Return the explicit structured meeting notes in the SMM condition."""
    if not explicit_smm_memory_enabled():
        return ""

    return (
        "Your structured shared mental model notes:\n"
        "These notes are your structured representation of the evolving "
        "team knowledge state. They summarize what has been established in the "
        "meeting, what information you know that has not yet been discussed, what each "
        "panel member has disclosed, current preferences separately from evidence, "
        "and unresolved decision issues.\n\n"
        "Treat these notes as a working summary, not as new candidate evidence "
        "and not as ground truth. If the notes conflict with the actual meeting "
        "history or your own interview notes, rely on the original evidence.\n\n"
        f"{read_agent_memory(agent_key)}\n\n"
    )


def _tracking_guidance_section() -> str:
    """Return matched baseline/treatment guidance for tracking the discussion."""
    if explicit_smm_memory_enabled():
        return (
            "Using the structured shared mental model:\n"
            "Use your structured notes to identify what the panel has already "
            "established, which candidates remain under-discussed, which criteria "
            "are unresolved, who has disclosed what, and what the next useful "
            "discussion focus should be. The notes should help you decide whether "
            "to share evidence, compare candidates, revise your recommendation, "
            "or ask a targeted tool question. Do not let a current preference or "
            "apparent majority substitute for criterion-level evidence.\n\n"
        )

    return (
        "Using the raw discussion history:\n"
        "Use the meeting discussion history below to track what the panel has "
        "already established, which candidates remain under-discussed, which "
        "criteria are unresolved, who has disclosed what, and what the next "
        "useful discussion focus should be. Reconstruct this from the transcript "
        "before deciding whether to share evidence, compare candidates, revise "
        "your recommendation, or ask a targeted tool question.\n\n"
    )


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _optional_system_prompt(system_prompt: str) -> str:
    """Include caller-provided extra role instructions when present."""
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        return ""
    return f"Additional role instructions:\n{system_prompt.strip()}\n\n"


def _latest_vote_for_agent(ctx, agent_key: str | None) -> str:
    """Return the latest recorded vote for an agent, or a placeholder."""
    if not agent_key:
        return "Unavailable"
    response = _get_state(ctx).get(f"{agent_key}_response", "")
    return extract_vote_from_response(response) or "Unavailable"


# ---------------------------------------------------------------------------
# Main scheduled discussion-turn prompt
# ---------------------------------------------------------------------------

def build_agent_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the full prompt for an agent's scheduled public discussion turn."""
    persona = _agent_persona(agent_key)
    agent_name = persona["name"]
    agent_role = persona["role"]

    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    available_info = [*public_info, *private_info]
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    vote_options = "|".join(candidates) if candidates else "candidate"

    discussion_history = build_public_discussion_history(ctx)
    extra_instructions = _optional_system_prompt(system_prompt)

    return (
        f"You are {agent_name}, {agent_role} at {AIRLINE_NAME}.\n"
        f"Internal agent identifier for metadata only: {agent_key}.\n\n"

        f"{extra_instructions}"

        "Role and setting:\n"
        f"{AIRLINE_NAME} is hiring one long-distance airline pilot. This is a "
        "safety-critical position, so the hiring panel must make a careful, "
        "evidence-based recommendation.\n\n"
        "Over the past week, you and the other panel members conducted individual "
        "candidate interviews, reviewed assessment notes, and discussed "
        "role-relevant situations with the candidates. You have candidate "
        "information available from the selection process; other panel members "
        "may have overlapping or different observations. Some of what you know "
        "may already be known by colleagues, and some may be known only to you "
        "until it is discussed.\n\n"
        "The panel has now blocked the next hour in a meeting room at company "
        "headquarters to agree on one final hiring recommendation. Treat this "
        "as a real professional HR selection meeting: structured, cooperative, "
        "concise, and focused on the quality of the hiring decision.\n\n"

        "Team objective:\n"
        "Help the panel combine distributed candidate information and reach the "
        "best joint recommendation. Bring relevant interview evidence into the "
        "meeting, ask colleagues for missing information when needed, compare "
        "candidates against the pilot selection criteria, and update your "
        "recommendation when the combined evidence supports it.\n\n"

        f"Hiring goal:\n{goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Current discussion round: {_round_number()}\n\n"

        f"{_selection_criteria_section()}"
        f"{_professional_hr_behavior_section()}"
        f"{_meeting_process_section()}"
        f"{_round_guidance_section()}"

        "Candidate information available to you:\n"
        "Treat this as your working notes for the meeting. Some items may overlap "
        "with what colleagues know, and some may be known only to you until you "
        "bring them into the discussion.\n"
        f"{_as_bullets(available_info)}\n\n"

        f"{_input_context_section()}"
        f"{_shared_communication_guidance_section()}"
        f"{_memory_block(agent_key)}"
        f"{_tracking_guidance_section()}"
        f"{_evidence_boundaries_section()}"
        f"{_tool_question_section(agent_key)}"

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        "Output requirements:\n"
        "Output only the two sections below. Do not add planning notes, hidden "
        "reasoning, explanations outside the sections, or any preamble.\n\n"

        f"{PUBLIC_MESSAGE_LABEL}:\n"
        f"{_public_message_template()}\n\n"

        f"{METADATA_JSON_LABEL}:\n"
        f"{{\"agent\": \"{agent_key}\", \"vote\": \"<{vote_options}>\"}}\n"
    )


# ---------------------------------------------------------------------------
# Passive memory-update prompt for the treatment condition
# ---------------------------------------------------------------------------

def build_memory_update_instruction(
    agent_key: str,
    ctx=None,
    latest_speaker_key: str | None = None,
) -> str:
    """Build the prompt for a passive structured-memory update."""
    persona = _agent_persona(agent_key)
    agent_name = persona["name"]
    agent_role = persona["role"]

    memory = read_agent_memory(agent_key)
    discussion_history = build_public_discussion_history(ctx)

    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    available_info = [*public_info, *private_info]
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    latest_speaker = latest_speaker_key or "unknown_agent"
    latest_speaker_display = (
        _agent_display_name(latest_speaker_key)
        if latest_speaker_key
        else "unknown panel member"
    )
    latest_vote = _latest_vote_for_agent(ctx, latest_speaker_key)

    return (
        f"You are {agent_name}, {agent_role} at {AIRLINE_NAME}.\n"
        f"Internal agent identifier for metadata only: {agent_key}.\n\n"

        "You are updating your structured shared mental model notes "
        "during the HR hiring-panel meeting. These notes are used to track the "
        "evolving team knowledge state. They are not a new evidence source and "
        "must not contain invented candidate information.\n\n"

        f"Hiring goal:\n{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        f"{_selection_criteria_section()}"

        "Candidate information available to you:\n"
        "Treat this as your working notes for the meeting. Some items may overlap "
        "with what colleagues know, and some may be known only to you until they "
        "are discussed.\n"
        f"{_as_bullets(available_info)}\n\n"

        f"Latest speaker: {latest_speaker} ({latest_speaker_display})\n"
        f"Latest speaker vote: {latest_vote}\n\n"

        "Your current structured shared mental model notes:\n"
        f"{memory}\n\n"

        f"{_input_context_section()}"

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        "Update instructions:\n"
        "Update your notes to reflect the latest public contribution and any "
        "public tool question-and-answer exchanges. Follow these rules exactly:\n\n"

        "1. Candidate-criterion evidence matrix:\n"
        "- Keep preferences and leading-candidate judgments out of this matrix; "
        "record only candidate evidence, concerns, unknowns, likely knowledge "
        "owners, and next best questions.\n"
        "- For each candidate and pilot criterion, track discussed evidence, "
        "counterevidence or concerns, what remains unknown or unclear, your own "
        "evidence not yet discussed, the likely knowledge owner if known, "
        "and the next best internal question.\n"
        "- Move candidate information that has been publicly shared into the "
        "discussed-evidence or counterevidence column for the relevant cell.\n"
        "- Keep relevant information you know in the not-yet-discussed evidence "
        "column until it appears in the public discussion.\n"
        "- If you are the latest speaker and you publicly shared something from "
        "your available information, remove that item from not-yet-discussed "
        "evidence or mark it as discussed.\n"
        "- Do not treat one agent lacking information as proof that evidence does "
        "not exist; mark it as unknown unless the relevant owner has been checked.\n"
        "- Do not add anything to evidence you know that is not present in the "
        "candidate information available to you.\n"
        "- Do not invent or infer candidate attributes.\n\n"

        "2. Information disclosure tracker:\n"
        "- Record what the latest speaker explicitly disclosed.\n"
        "- Record public tool answers if they revealed candidate information.\n"
        "- Do not speculate about what any speaker still knows but has not discussed.\n\n"

        "3. My current position:\n"
        "- Update only if you are the latest speaker.\n"
        "- Record your current recommendation, main stated reason, confidence or "
        "uncertainty if stated, and what evidence could change your view if stated.\n\n"

        "4. Other agents' positions:\n"
        "- Update the latest speaker's row with their stated recommendation and reason.\n"
        "- Record only what they explicitly stated. Do not infer hidden motives or "
        "unstated evidence.\n\n"

        "5. Group knowledge state:\n"
        "- Track which candidates have been discussed and which remain under-discussed.\n"
        "- Track candidate strengths, concerns, unresolved criteria, contested "
        "interpretations, and criterion-level gaps.\n"
        "- Track whether the panel is ready for consensus based on available "
        "evidence, not merely whether votes are aligning.\n"
        "- Identify open questions or next-step comparison gaps that could affect "
        "the final recommendation.\n\n"

        "Return only a JSON object with these exact keys:\n"
        "candidate_evidence_table, information_disclosure_tracker, "
        "my_current_position, other_agents_positions, group_knowledge_state.\n\n"
        "Each value must be the complete markdown body for that section, without "
        "the section heading. Do not wrap the JSON in a code fence. Do not add "
        "commentary. Do not call tools."
    )


# ---------------------------------------------------------------------------
# Tool-response prompt
# ---------------------------------------------------------------------------

def build_agent_tool_instruction(
    agent_key: str,
    ctx=None,
    system_prompt: str = "",
) -> str:
    """Build the prompt for an agent answering a targeted tool question."""
    persona = _agent_persona(agent_key)
    agent_name = persona["name"]
    agent_role = persona["role"]

    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    available_info = [*public_info, *private_info]
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    discussion_history = build_public_discussion_history(ctx)
    extra_instructions = _optional_system_prompt(system_prompt)

    return (
        f"You are {agent_name}, {agent_role} at {AIRLINE_NAME}.\n"
        f"Internal agent identifier for metadata only: {agent_key}.\n\n"

        f"{extra_instructions}"

        "Another hiring-panel member has asked you a targeted question during "
        "the meeting. Answer cooperatively and directly, as a serious HR panel "
        "member would.\n\n"

        f"Hiring goal:\n{goal}\n"
        f"Candidates: {', '.join(candidates)}\n\n"

        f"{_selection_criteria_section()}"

        "Candidate information available to you:\n"
        "Treat this as your working notes for the meeting. Some items may overlap "
        "with what colleagues know, and some may be known only to you until they "
        "are discussed.\n"
        f"{_as_bullets(available_info)}\n\n"

        f"{_input_context_section()}"
        f"{_shared_communication_guidance_section()}"
        f"{_memory_block(agent_key)}"

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        "Answer rules:\n"
        f"Answer only using information explicitly present in {_grounding_sources()}. "
        "Answer the specific question first. If you do not have the exact item "
        "asked for but you do have nearby relevant evidence on the same "
        "candidate or criterion, say that clearly and volunteer that evidence. "
        "Do not dump unrelated notes.\n\n"
        "If you have relevant information, share it concisely. If you do not "
        "have exact information on the topic asked, say so directly and then "
        "share the closest relevant observation if one exists. If the question "
        "asks for external records, incident reports, simulator debriefs, "
        "training plans, or hypothetical examples not present in your notes or "
        "the discussion, say you do not have that external information, but still "
        "share any internal note that bears on the same criterion.\n\n"
        "Do not invent or infer candidate attributes. Do not treat absence from "
        "your own notes as evidence that a candidate lacks the trait. Do not ask "
        "a follow-up question in this tool answer.\n\n"
        "Output only the direct answer. No metadata, no section headers, no "
        "planning notes."
    )
