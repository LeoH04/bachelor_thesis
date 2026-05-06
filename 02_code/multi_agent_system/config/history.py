"""Record and format public discussion history."""

from .make_session_log import CHAT_LOG_FILE
from .metrics import metrics
from .response_text import (
    METADATA_JSON_LABEL_RE,
    _drop_thought_parts,
    _extract_public_message,
    _public_value_text,
    _visible_text_from_parts,
)
from .task import AGENT_KEYS
from .trace import log_event

PUBLIC_DISCUSSION_STATE_KEY = "public_discussion_history"


def _round_number() -> int:
    """Return the current human-readable discussion round number."""
    return metrics.loop_count + 1


def _get_state(ctx) -> dict:
    """Return the Google ADK context state, or an empty state without a context."""
    if ctx is None:
        return {}

    return ctx.state


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


def reset_public_discussion_history(state: dict) -> None:
    """Clear the public discussion transcript stored in the simulation state."""
    if state is not None:
        state[PUBLIC_DISCUSSION_STATE_KEY] = []


def _append_chat_entry(round_number: int, speaker: str, message: str) -> None:
    """Append one public discussion entry to the human-readable chat markdown."""
    CHAT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHAT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"## Round {round_number} - {speaker}\n\n{message.strip()}\n\n")


def record_public_discussion_response(callback_context, llm_response) -> None:
    """Append only a normal agent turn's visible final message to shared state."""
    agent_name = getattr(callback_context, "agent_name", None)
    if agent_name not in AGENT_KEYS:
        return None

    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    visible_parts = _drop_thought_parts(content, parts)
    text = _visible_text_from_parts(visible_parts)

    if not METADATA_JSON_LABEL_RE.search(text):
        return llm_response

    public_message = _extract_public_message(text)
    if not public_message:
        return llm_response

    state = _get_state(callback_context)
    history = list(state.get(PUBLIC_DISCUSSION_STATE_KEY, []))
    round_number = _round_number()
    history.append(
        {
            "round": round_number,
            "agent": agent_name,
            "message": public_message,
        }
    )
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    _append_chat_entry(round_number, _agent_label(agent_name), public_message)
    log_event(
        "public_discussion_message",
        round=round_number,
        agent=agent_name,
        message=public_message,
    )
    metrics.record_agent_turn()
    return llm_response


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
    message_parts = [f"Question and answer: {caller_label} asked {callee_label}."]
    if question:
        message_parts.append(f"Question: {question}")
    if answer:
        message_parts.append(f"Answer: {answer}")

    state = _get_state(tool_context)
    history = list(state.get(PUBLIC_DISCUSSION_STATE_KEY, []))
    round_number = _round_number()
    callee_key = _agent_key(callee_name)
    caller_key = _agent_key(caller_name)
    message = "\n".join(message_parts)
    history.append(
        {
            "round": round_number,
            "agent": callee_key,
            "message": message,
            "source": "agent_tool_call",
            "caller": caller_key,
        }
    )
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    _append_chat_entry(
        round_number,
        f"Tool: {caller_label} -> {callee_label}",
        message,
    )
    log_event(
        "public_tool_exchange",
        round=round_number,
        caller=caller_key,
        callee=callee_key,
        question=question,
        answer=answer,
        message=message,
    )
    return None

def build_public_discussion_history(ctx) -> str:
    """Format the stored public discussion transcript for inclusion in prompts."""
    state = _get_state(ctx)
    history = state.get(PUBLIC_DISCUSSION_STATE_KEY, [])
    if not history:
        return "- No discussion contributions yet."

    lines = []
    for item in history:
        if not isinstance(item, dict):
            continue
        round_number = item.get("round", "?")
        agent = str(item.get("agent", "unknown_agent")).replace("_", " ").title()
        message = str(item.get("message", "")).strip()
        if message:
            lines.append(f"- Round {round_number}, {agent}: {message}")

    return "\n".join(lines) if lines else "- No discussion contributions yet."
