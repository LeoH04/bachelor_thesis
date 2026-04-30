"""Load task context and build prompts, memory files, and shared state."""

import json
import re
import shutil
from pathlib import Path
from typing import Iterable

from .make_session_log import SHARED_MENTAL_MODELS_DIR, update_run_metadata
from .metrics import metrics

TASK_PATH = Path(__file__).parent / "hidden_profile_task.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_AGENT_MEMORIES_ARCHIVED = False

PUBLIC_DISCUSSION_STATE_KEY = "public_discussion_history"


def load_task() -> dict:
    """Load the hidden-profile task definition from the local JSON file."""
    with TASK_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


TASK = load_task()
AGENT_KEYS = ["agent_1", "agent_2", "agent_3", "agent_4"]


def _as_bullets(items: Iterable[str]) -> str:
    """Render an iterable of strings as markdown bullets, or a placeholder if empty."""
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def _agent_memory_path(agent_key: str) -> Path:
    """Return the markdown memory file path for the given agent key."""
    return PROJECT_ROOT / "agents" / "discussion" / f"{agent_key}.md"


def _round_number() -> int:
    """Return the current human-readable discussion round number."""
    return metrics.loop_count + 1


def _get_state(ctx) -> dict:
    """Return the Google ADK context state, or an empty state without a context."""
    if ctx is None:
        return {}

    return ctx.state


def _clean_public_message(text: str) -> str:
    """Strip metadata and tool traces from agent text before storing it publicly."""
    text = re.sub(r"METADATA_JSON:\s*\{.*?\}\s*", "", text, flags=re.DOTALL)

    visible_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "For context:":
            continue
        if "called tool `" in stripped or "tool returned result:" in stripped:
            continue
        visible_lines.append(line.rstrip())

    return "\n".join(visible_lines).strip()


def _agent_label(agent_name: str | None) -> str:
    """Return a readable discussion label for an ADK agent name."""
    if not agent_name:
        return "Unknown Agent"

    return agent_name.removesuffix("_tool").replace("_", " ").title()


def _agent_key(agent_name: str | None) -> str:
    """Return the scheduled-agent key for normal and tool agent names."""
    if not agent_name:
        return "unknown_agent"

    return agent_name.removesuffix("_tool")


def _public_value_text(value: object) -> str:
    """Render a tool argument or result as concise public discussion text."""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = _clean_public_message(str(item))
            if item_text:
                parts.append(f"{key}: {item_text}")
        return "; ".join(parts).strip()

    return _clean_public_message(str(value)).strip()


def reset_public_discussion_history(state: dict) -> None:
    """Clear the public discussion transcript stored in the simulation state."""
    if state is not None:
        state[PUBLIC_DISCUSSION_STATE_KEY] = []


def record_public_discussion_response(callback_context, llm_response) -> None:
    """Append only a normal agent turn's visible final message to shared state."""
    agent_name = getattr(callback_context, "agent_name", None)
    if agent_name not in AGENT_KEYS:
        return None

    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", None) or []
    text = "\n".join(
        part.text for part in parts if getattr(part, "text", None)
    ).strip()

    if "METADATA_JSON:" not in text:
        return None

    public_message = _clean_public_message(text)
    if not public_message:
        return None

    state = _get_state(callback_context)
    history = list(state.get(PUBLIC_DISCUSSION_STATE_KEY, []))
    history.append(
        {
            "round": _round_number(),
            "agent": agent_name,
            "message": public_message,
        }
    )
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    metrics.record_agent_turn()
    return None


def record_public_tool_exchange(
    tool_context,
    caller_name: str | None,
    callee_name: str | None,
    args: object,
    result: object,
) -> None:
    """Append an agent-to-agent tool exchange to the public discussion state."""
    question = _public_value_text(args)
    answer = _public_value_text(result)
    if not question and not answer:
        return None

    caller_label = _agent_label(caller_name)
    callee_label = _agent_label(callee_name)
    message_parts = [f"Tool exchange: {caller_label} asked {callee_label}."]
    if question:
        message_parts.append(f"Question: {question}")
    if answer:
        message_parts.append(f"Answer: {answer}")

    state = _get_state(tool_context)
    history = list(state.get(PUBLIC_DISCUSSION_STATE_KEY, []))
    history.append(
        {
            "round": _round_number(),
            "agent": _agent_key(callee_name),
            "message": "\n".join(message_parts),
            "source": "agent_tool_call",
            "caller": _agent_key(caller_name),
        }
    )
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    return None


def build_latest_public_discussion_message(ctx) -> str:
    """Format the latest public discussion message for passive memory updates."""
    state = _get_state(ctx)
    history = state.get(PUBLIC_DISCUSSION_STATE_KEY, [])
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        round_number = item.get("round", "?")
        agent = str(item.get("agent", "unknown_agent")).replace("_", " ").title()
        message = str(item.get("message", "")).strip()
        if message:
            return f"Round {round_number}, {agent}: {message}"

    return "No public discussion message is available."


def build_public_discussion_history(ctx) -> str:
    """Format the stored public discussion transcript for inclusion in prompts."""
    state = _get_state(ctx)
    history = state.get(PUBLIC_DISCUSSION_STATE_KEY, [])
    if not history:
        return "- No public discussion messages yet."

    lines = []
    for item in history:
        if not isinstance(item, dict):
            continue
        round_number = item.get("round", "?")
        agent = str(item.get("agent", "unknown_agent")).replace("_", " ").title()
        message = str(item.get("message", "")).strip()
        if message:
            lines.append(f"- Round {round_number}, {agent}: {message}")

    return "\n".join(lines) if lines else "- No public discussion messages yet."


def build_memory_template(agent_key: str, round_number: int | None = None) -> str:
    """Create the initial structured markdown memory for one agent."""
    round_number = round_number or _round_number()
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    candidate_rows = "\n".join(
        f"| {candidate} |  |  |  |  |" for candidate in candidates
    )

    return (
        f"# Shared Mental Model (Agent {agent_key.split('_')[-1]}, Round {round_number})\n\n"
        "## Task Summary\n"
        f"Goal\n{goal}\n\n"
        f"Candidates\n{_as_bullets(candidates)}\n\n"
        f"Public Information\n{_as_bullets(public_info)}\n\n"
        f"Private Information\n{_as_bullets(private_info)}\n\n"
        "## Candidate Summary Table\n"
        "| Candidate | Evidence For | Evidence Against | Fit for Role | Notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{candidate_rows}\n\n"
        "## Current Preference\n"
        "Leading Candidate\n- \n\n"
        "Rationale\n- \n\n"
        "Confidence (percent)\n- \n\n"
        "Decision Readiness\n- \n\n"
        "Uncertainties\n- \n\n"
        "## Open Questions\n"
        "Missing evidence\n- \n\n"
        "What would change the decision\n- \n\n"
        "## Next-Step Focus\n"
        "What to ask or look for in the next round\n- \n"
    )


def read_agent_memory(agent_key: str, round_number: int | None = None) -> str:
    """Read an agent's memory file, falling back to a fresh template if needed."""
    path = _agent_memory_path(agent_key)
    if not path.exists():
        return build_memory_template(agent_key, round_number)

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return build_memory_template(agent_key, round_number)

    return content


def write_agent_memory(agent_key: str, content: str) -> None:
    """Persist a full replacement markdown memory for the given agent."""
    path = _agent_memory_path(agent_key)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def archive_agent_memories() -> Path | None:
    """Copy final agent memory markdown files into raw shared-mental-model data."""
    global _AGENT_MEMORIES_ARCHIVED

    destination = SHARED_MENTAL_MODELS_DIR
    if _AGENT_MEMORIES_ARCHIVED:
        return None

    destination.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for agent_key in AGENT_KEYS:
        source = _agent_memory_path(agent_key)
        if source.exists():
            target = destination / source.name
            shutil.copy2(source, target)
            copied_files.append(str(target))

    _AGENT_MEMORIES_ARCHIVED = True
    update_run_metadata(
        {
            "shared_mental_models_archived": True,
            "shared_mental_model_files": copied_files,
        }
    )
    return destination


def reset_all_agent_memories(round_number: int | None = 1) -> None:
    """Reset every agent memory file to a fresh template for the target round."""
    for agent_key in AGENT_KEYS:
        template = build_memory_template(agent_key, round_number)
        write_agent_memory(agent_key, template)


def build_agent_instruction(agent_key: str, ctx=None) -> str:
    """Build the full prompt for an agent's scheduled public discussion turn."""
    round_number = _round_number()
    memory = read_agent_memory(agent_key, round_number)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    other_agents = [key for key in AGENT_KEYS if key != agent_key]

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"
        "Task context (use in your reasoning):\n"
        f"Goal: {goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Public information:\n{_as_bullets(public_info)}\n"
        f"Private information:\n{_as_bullets(private_info)}\n\n"
        f"You may call other agents as tools: {', '.join(other_agents)}.\n"
        "If you have a specific question, ask it via the relevant agent tool.\n"
        "Agent-tool exchanges are public discussion messages and will be included "
        "in the shared memory updates.\n"
        "Previous internal memory:\n"
        f"{memory}\n\n"
        "Visible discussion history (public messages, including public agent-tool "
        "exchanges; memory updates are intentionally hidden):\n"
        f"{discussion_history}\n\n"
        "Read the visible discussion history and your previous internal memory, then "
        "give a short public opinion. The orchestrator updates all agent memories "
        "after your public message, so do not attempt to update memory during this "
        "speaking turn.\n\n"
        "End with this exact metadata format:\n\n"
        "METADATA_JSON:\n"
        f"{{\"agent\": \"{agent_key}\", \"vote\": \"<Alice|Bob|Carol|Eve|Dave>\"}}\n"
    )


def build_memory_update_instruction(agent_key: str, ctx=None) -> str:
    """Build the prompt for a passive memory update after a public message."""
    round_number = _round_number()
    memory = read_agent_memory(agent_key, round_number)
    latest_message = build_latest_public_discussion_message(ctx)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    memory_tool = f"set_{agent_key}_memory"

    return (
        f"You are {agent_key.replace('_', ' ').title()} performing a passive memory update.\n\n"
        "Task context:\n"
        f"Goal: {goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Public information:\n{_as_bullets(public_info)}\n"
        f"Private information:\n{_as_bullets(private_info)}\n\n"
        "Previous internal memory:\n"
        f"{memory}\n\n"
        "Latest public discussion message:\n"
        f"{latest_message}\n\n"
        "Visible discussion history for context:\n"
        f"{discussion_history}\n\n"
        "Update your previous internal memory incrementally, as if revising an "
        "existing understanding during a meeting. Preserve prior facts, preferences, "
        "and uncertainties unless new information contradicts them. Add only salient "
        "new information from any public discussion messages not yet reflected in "
        "your memory, including public agent-tool exchanges, plus your private "
        "knowledge where relevant. Revise confidence and decision readiness only "
        "when justified. Do not copy the full discussion history into memory. Do "
        "not rewrite the memory from scratch or turn it into a fresh summary.\n"
        f"Call the {memory_tool} tool with the complete Shared Mental Model markdown "
        "after these incremental revisions.\n"
        "Do not add a new public discussion contribution. After the tool call, "
        "respond only with: MEMORY_UPDATED"
    )


def build_agent_tool_instruction(agent_key: str, ctx=None) -> str:
    """Build the prompt for an agent answering another agent through a tool call."""
    round_number = _round_number()
    memory = read_agent_memory(agent_key, round_number)
    discussion_history = build_public_discussion_history(ctx)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    return (
        f"You are {agent_key.replace('_', ' ').title()} responding to another agent's question.\n\n"
        "Task context (use in your answer):\n"
        f"Goal: {goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Public information:\n{_as_bullets(public_info)}\n"
        f"Private information:\n{_as_bullets(private_info)}\n\n"
        "Previous internal memory:\n"
        f"{memory}\n\n"
        "Visible discussion history (public messages, including public agent-tool "
        "exchanges; memory updates are intentionally hidden):\n"
        f"{discussion_history}\n\n"
        "Answer the question directly and concisely using the same context you would "
        "have during a normal discussion turn. Your answer will be recorded as part "
        "of the public discussion, and the orchestrator will update all agent "
        "memories after the speaking agent's public turn.\n"
        "Do not update memory during this tool response. Do not include metadata or "
        "special formatting in your response."
    )
