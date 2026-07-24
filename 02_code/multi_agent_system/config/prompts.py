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

Important design principle:
Each public turn should be small. The whole meeting should be systematic.
Agents should not dump all facts at once, but the panel should gradually cover
all candidates before final convergence.
"""

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
        "on other safety-relevant criteria. Do not reject a candidate only because "
        "one source lacks information about them on a criterion. Use the panel "
        "discussion to combine distributed observations before settling on a "
        "recommendation.\n\n"
    )


def _professional_hr_behavior_section() -> str:
    """Return general professional behavior instructions."""
    return (
        "Professional behavior:\n"
        "Act like a serious HR recruiter in a safety-critical hiring meeting. "
        "Be concise, cooperative, evidence-based, and willing to revise your "
        "recommendation when the combined panel evidence supports it.\n\n"
    )


# ---------------------------------------------------------------------------
# Meeting process
# ---------------------------------------------------------------------------

def _meeting_process_section() -> str:
    """Return condition-neutral meeting process rules."""
    return (
        "Meeting process:\n"
        "This is a live HR selection meeting, not a written evidence inventory. "
        "The goal is not only to mention candidate facts, but to deliberate: "
        "state a current recommendation, respond to colleagues, argue for or "
        "against candidates using evidence, and try to move the panel toward the "
        "best joint hiring decision.\n\n"

        "Discussion rhythm:\n"
        "In each public turn, make one focused argumentative contribution. "
        "Do not simply introduce a new fact in isolation. Connect your point to "
        "the current group discussion and explain what it means for the hiring "
        "recommendation.\n\n"

        "A useful public contribution should normally include:\n"
        "- your current recommendation or whether your recommendation is changing,\n"
        "- a reference to the current discussion, such as agreeing with, challenging, "
        "or building on another panel member's point,\n"
        "- one or two explicit candidate facts as evidence,\n"
        "- and a clear implication for which candidate the panel should prefer.\n\n"

        "How to interact with others:\n"
        "From Round 2 onward, explicitly react to at least one previous contribution "
        "whenever possible. You may agree, disagree, qualify, or build on it. "
        "For example, if another member supports Candidate A because of a strength, "
        "you may argue that this strength is outweighed by a cooperation concern, "
        "or compare Candidate A with another candidate who fits the pilot role more "
        "evenly. Do not ignore the existing discussion and simply add unrelated facts.\n\n"

        "Candidate coverage rule:\n"
        "The panel should still cover Candidate A, Candidate B, Candidate C, and "
        "Candidate D before treating any recommendation as final. However, coverage "
        "should happen through discussion and comparison, not through isolated fact "
        "dumping. When you introduce an under-discussed candidate, explain whether "
        "that candidate should become a stronger option, a weaker option, or a "
        "comparison point against the current leading candidate.\n\n"

        "How to argue about a candidate:\n"
        "When focusing on a candidate, do not list every fact you know. Instead, "
        "make a case. Explain whether the fact supports or weakens that candidate "
        "for the long-distance pilot role, and compare it with the strongest "
        "alternative when useful. Try to convince the panel, but remain open to "
        "being convinced by better combined evidence.\n\n"

        "Tool-use during discussion:\n"
        "If a relevant criterion is unclear, first check your own notes. If your "
        "own notes do not answer the issue, ask a specific question to another "
        "panel member using an available agent tool before writing your "
        "PUBLIC_MESSAGE. Use tool answers to strengthen, weaken, or revise an "
        "argument in the public discussion.\n\n"

        "Recommendation behavior:\n"
        "Your vote is your current provisional recommendation, not a fixed "
        "position. Your PUBLIC_MESSAGE must make your vote understandable. "
        "If your vote stays the same, explain why the latest discussion still "
        "supports it. If your vote changes, explain which shared evidence changed "
        "your view. Do not vote for a candidate without giving a public reason "
        "that points in the same direction.\n\n"
    )

def _public_message_requirements_section() -> str:
    """Return requirements for the public discussion message."""
    return (
        "PUBLIC_MESSAGE requirements:\n"
        "Write like a real panel member in the meeting. Your message should be "
        "a short argumentative contribution, not a neutral evidence note.\n\n"

        "Your PUBLIC_MESSAGE must:\n"
        "- state or clearly imply your current hiring recommendation,\n"
        "- refer to the existing discussion when possible,\n"
        "- use explicit candidate facts as evidence,\n"
        "- explain why the evidence supports, weakens, or changes a candidate's case,\n"
        "- and be consistent with your METADATA_JSON vote.\n\n"

        "From Round 2 onward, avoid starting a completely new point without "
        "connecting it to the prior discussion. Prefer formulations such as: "
        "'I agree with...', 'I am less convinced by...', 'This changes my view because...', "
        "'Compared with...', or 'I would still choose... because...'.\n\n"

        "Do not merely say that a candidate has a trait. Explain what that trait "
        "means for the hiring decision.\n\n"
    )

# ---------------------------------------------------------------------------
# Evidence boundaries and tool-question behavior
# ---------------------------------------------------------------------------

def _grounding_sources() -> str:
    """Return the evidence sources agents may use."""
    return (
        "your own candidate notes, the public meeting discussion, and public "
        "tool answers"
    )


def _evidence_boundaries_section() -> str:
    """Return strict grounding instructions."""
    return (
        "Evidence boundaries:\n"
        f"Use only explicit candidate facts from {_grounding_sources()}. "
        "Do not invent candidate traits, examples, explanations, background "
        "stories, aviation experience, training plans, simulator results, "
        "incident reports, technologies, risk mitigations, or any other details "
        "not explicitly given.\n\n"

        "The candidate information consists only of facts. Once a fact is known, "
        "there is no additional hidden detail behind it. Do not create examples "
        "or explanations around a fact.\n\n"

        "If a fact is absent from your own notes, do not infer that the candidate "
        "lacks that trait. Another panel member may have relevant information. "
        "If another panel member says they do not know, that only means this "
        "specific person does not have that information.\n\n"

        "The panel should make the recommendation from the candidate information "
        "available in the meeting, public discussion, and public tool answers. "
        "Do not delay the decision by asking for external records, future checks, "
        "or information that is not part of the available candidate materials.\n\n"
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
            "Tool use:\n"
            "No other interviewer tools are available in this run.\n\n"
        )

    return (
        "Tool use:\n"
        f"You may ask targeted questions to: {', '.join(other_agent_tools)}.\n\n"

        "If you need information from another panel member, ask through the "
        "available agent tool before writing your PUBLIC_MESSAGE. Do not write "
        "questions to other agents inside PUBLIC_MESSAGE, because public questions "
        "are not answered unless they are made through a tool call.\n\n"

        "Ask only specific questions about a candidate, criterion, strength, "
        "concern, or comparison. Do not ask for another agent's full notes and "
        "do not ask which candidate is correct.\n\n"

        "After receiving a tool answer, use it if it is relevant to the current "
        "discussion step. Summarize the relevant fact or uncertainty in your "
        "PUBLIC_MESSAGE; do not include unresolved questions there.\n\n"
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
        "These notes are your structured representation of the evolving team "
        "knowledge state. They track candidate coverage, discussed strengths and "
        "concerns, relevant own facts not yet discussed, information distribution, "
        "current positions, and whether the panel is ready for convergence.\n\n"

        "Use these notes as a meeting navigation aid. They help you decide what "
        "the panel should discuss next. They are not new candidate evidence and "
        "not ground truth. If the notes conflict with your own candidate notes, "
        "the public discussion, or a public tool answer, rely on the original "
        "evidence.\n\n"

        f"{read_agent_memory(agent_key)}\n\n"
    )


def _tracking_guidance_section() -> str:
    """Return matched baseline/treatment guidance for tracking the discussion."""
    if explicit_smm_memory_enabled():
        return (
            "Using the structured shared mental model:\n"
            "Before speaking, use your structured notes to decide the next "
            "discussion move. Check them in this order:\n"
            "1. Which candidate is currently leading, and why?\n"
            "2. Which colleague's point should you agree with, challenge, or build on?\n"
            "3. Which candidate is the strongest alternative to the current leader?\n"
            "4. Which explicit fact from your notes could strengthen or weaken the current argument?\n"
            "5. Which candidates are still under-discussed?\n"
            "6. Which open question should be asked through a targeted tool call?\n"
            "7. Is the panel actually ready for convergence, or only forming an early majority?\n\n"

            "Use the SMM to make the meeting systematic. Each public turn should "
            "remain small, but across the meeting the panel should cover all "
            "candidates before final convergence.\n\n"
        )

    return (
        "Using the raw discussion history:\n"
        "Before speaking, reconstruct from the public discussion what the panel "
        "has already argued, not only what facts have been mentioned. Identify "
        "the current leading candidate, the strongest alternative, which colleague's "
        "point you should agree with or challenge, which candidates remain "
        "under-discussed, and what evidence would best move the decision forward.\n\n"
    )


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

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

    return (
        f"You are {agent_name}, {agent_role} at {AIRLINE_NAME}.\n"
        f"Internal agent identifier for metadata only: {agent_key}.\n\n"

        "Role and setting:\n"
        f"{AIRLINE_NAME} is hiring one long-distance airline pilot. This is a "
        "safety-critical position, so the hiring panel must make a careful, "
        "evidence-based recommendation.\n\n"

        "You and the other panel members are HR recruiters who have interviewed "
        "the four candidates and reviewed role-relevant assessment notes. Each "
        "recruiter has their own notes. Some observations overlap across panel "
        "members, while other observations are known only to one recruiter until "
        "they are brought into the discussion.\n\n"

        "The panel has now blocked the next hour in a meeting room at company "
        "headquarters to agree on one final hiring recommendation. The goal is "
        "to discuss the candidates systematically, combine the distributed "
        "candidate facts, and converge on the one candidate who should be hired.\n\n"

        "Team objective:\n"
        "Help the panel reach the best joint recommendation. Bring relevant "
        "interview evidence into the meeting, ask colleagues for missing "
        "information when needed, compare candidates against the pilot selection "
        "criteria, and update your recommendation when the combined evidence "
        "supports it.\n\n"

        f"Hiring goal:\n{goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Current discussion round: {_round_number()}\n\n"

        f"{_selection_criteria_section()}"
        f"{_professional_hr_behavior_section()}"
        f"{_meeting_process_section()}"

        "Candidate information available to you:\n"
        "Treat this as your working notes for the meeting. Some items may overlap "
        "with what colleagues know, and some may be known only to you until you "
        "bring them into the discussion.\n"
        f"{_as_bullets(available_info)}\n\n"

        f"{_memory_block(agent_key)}"
        f"{_tracking_guidance_section()}"
        f"{_evidence_boundaries_section()}"
        f"{_tool_question_section(agent_key)}"

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        f"{_public_message_requirements_section()}"
        
        "Output requirements:\n"
        "Output only the two sections below. Do not add planning notes, hidden "
        "reasoning, explanations outside the sections, or any preamble.\n\n"

        f"{PUBLIC_MESSAGE_LABEL}:\n"

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

        "You are updating your structured shared mental model notes during the "
        "HR hiring-panel meeting. These notes are used to track the evolving "
        "team knowledge state and to guide the next discussion move. They are "
        "not a new evidence source and must not contain invented candidate "
        "information.\n\n"

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

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        "Update instructions:\n"
        "Update your structured shared mental model to reflect the latest public "
        "contribution and any public tool question-and-answer exchanges. Preserve "
        "the five-section structure exactly. Follow these rules:\n\n"

        "1. Candidate Review Status:\n"
        "- For each candidate, track discussed strengths, discussed concerns, "
        "relevant own facts not yet discussed, unclear or missing criteria, and "
        "the next useful discussion move.\n"
        "- Move facts out of 'Relevant own facts not yet discussed' once they "
        "appear in the public discussion or in a public tool answer.\n"
        "- Do not list every fact you know. Include only facts that are relevant "
        "for guiding the next discussion step.\n"
        "- Do not invent or infer candidate attributes.\n\n"

        "2. Candidate Coverage Checklist:\n"
        "- Track whether each candidate has been discussed at all.\n"
        "- Track whether strengths have been discussed.\n"
        "- Track whether concerns have been discussed.\n"
        "- Track whether the candidate has been compared with another candidate.\n"
        "- Mark a candidate as still under-discussed if the panel has not yet "
        "covered enough evidence to evaluate that candidate fairly.\n\n"

        "3. Information Distribution:\n"
        "- Record what each agent has explicitly shared.\n"
        "- Record relevant open questions for an agent only if that agent may "
        "reasonably have relevant information based on the discussion.\n"
        "- Do not speculate about hidden information. Do not assume an agent has "
        "information unless the discussion suggests asking them would be useful.\n\n"

        "4. Current Positions:\n"
        "- Track each agent's current vote, stated reason, and uncertainty or "
        "what could change their view.\n"
        "- Record only what agents explicitly stated in public messages or public "
        "tool answers.\n"
        "- Do not infer hidden motives or unstated reasons.\n\n"

        "5. Group Decision State:\n"
        "- Track the current leading candidate and strongest alternative.\n"
        "- Track the main reason supporting the leading candidate and the main "
        "concern about that candidate.\n"
        "- Track the main unresolved comparison.\n"
        "- Track which candidates still need discussion.\n"
        "- Track important criteria still unclear.\n"
        "- Mark 'Ready for convergence?' as Yes only if all candidates have been "
        "discussed and the leading candidate has been compared with the strongest "
        "alternative using available evidence.\n\n"

        "Important evidence rules:\n"
        "- Use only your own candidate notes, the public discussion, and public "
        "tool answers.\n"
        "- The candidate information consists only of facts. Do not create "
        "additional examples or explanations around a fact.\n"
        "- If information is absent from one agent's notes, this does not mean "
        "the candidate lacks that trait. Another agent may know it.\n\n"

        "Return only a JSON object with these exact keys:\n"
        "candidate_review_status, candidate_coverage_checklist, "
        "information_distribution, current_positions, group_decision_state.\n\n"

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

    return (
        f"You are {agent_name}, {agent_role} at {AIRLINE_NAME}.\n"
        f"Internal agent identifier for metadata only: {agent_key}.\n\n"

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

        "Meeting discussion so far:\n"
        f"{discussion_history}\n\n"

        "Answer rules:\n"
        f"Answer only using explicit candidate facts from {_grounding_sources()}. "
        "Answer the specific question first. If you do not have the exact item "
        "asked for but you do have nearby relevant evidence on the same candidate "
        "or criterion, say that clearly and volunteer that evidence. Do not dump "
        "unrelated notes.\n\n"

        "If you do not have information on the topic asked, say so directly. "
        "This only means that you personally do not have that information; it "
        "does not mean the candidate lacks the trait. Do not infer negative "
        "evidence from missing information.\n\n"

        "Do not invent candidate attributes, examples, explanations, or external "
        "information. Do not ask a follow-up question in this tool answer.\n\n"

        "Output only the direct answer. No metadata, no section headers, no "
        "planning notes."
    )