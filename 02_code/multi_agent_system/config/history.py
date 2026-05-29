"""Record and format public discussion history."""

from .context_transparency import input_history_scope, thought_history_enabled
from .make_session_log import CHAT_LOG_FILE
from .metrics import metrics
from .response_text import (
    METADATA_JSON_LABEL_RE,
    _drop_thought_parts,
    _extract_public_message,
    _public_value_text,
    _strip_metadata_json_section,
    _thought_text_from_parts,
    _visible_text_from_parts,
)
from .task import AGENT_KEYS
from .trace import log_event

PUBLIC_DISCUSSION_STATE_KEY = "public_discussion_history"
TOOL_RESPONSE_THOUGHTS_STATE_KEY = "tool_response_thoughts"
THOUGHT_HISTORY_COUNT_STATE_KEY = "thought_history_items"


def _round_number() -> int:
    """Return the current human-readable discussion round number."""
    return metrics.loop_count + 1


def _get_state(ctx) -> dict:
    """Return the Google ADK context state, or an empty state without a context."""
    if ctx is None:
        return {}

    return ctx.state


def strip_adk_for_context(callback_context, llm_request) -> None:
    """Remove ADK's generated multi-agent context block before model calls."""
    llm_request.contents = [
        content
        for content in llm_request.contents
        if not _is_adk_for_context_content(content)
    ]
    return None


def _is_adk_for_context_content(content) -> bool:
    if isinstance(content, dict):
        parts = list(content.get("parts") or [])
        role = content.get("role")
    else:
        parts = list(getattr(content, "parts", None) or [])
        role = getattr(content, "role", None)
    if not parts:
        return False

    return role == "user" and any(
        _part_text(part).strip().lower() == "for context:"
        for part in parts
    )


def _part_text(part: object) -> str:
    """Return text from an ADK part object or serialized part dictionary."""
    if isinstance(part, dict):
        return str(part.get("text") or "")
    return str(getattr(part, "text", "") or "")


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


def _record_thought_history_item(state: dict) -> int:
    """Increment the run-local count of thought-bearing history entries."""
    try:
        count = int(state.get(THOUGHT_HISTORY_COUNT_STATE_KEY, 0) or 0) + 1
    except (TypeError, ValueError):
        count = 1
    state[THOUGHT_HISTORY_COUNT_STATE_KEY] = count
    return count


def reset_public_discussion_history(state: dict) -> None:
    """Clear the public discussion transcript stored in the simulation state."""
    if state is not None:
        state[PUBLIC_DISCUSSION_STATE_KEY] = []
        state[TOOL_RESPONSE_THOUGHTS_STATE_KEY] = {}
        state[THOUGHT_HISTORY_COUNT_STATE_KEY] = 0


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
    thoughts = _thought_text_from_parts(parts) if thought_history_enabled() else ""

    if not METADATA_JSON_LABEL_RE.search(text):
        return llm_response

    public_message = _extract_public_message(text)
    if not public_message:
        return llm_response
    discussion_message = _strip_metadata_json_section(public_message)
    if not discussion_message:
        return llm_response

    state = _get_state(callback_context)
    history = list(state.get(PUBLIC_DISCUSSION_STATE_KEY, []))
    round_number = _round_number()
    history_item = {
        "round": round_number,
        "agent": agent_name,
        "message": discussion_message,
    }
    if thoughts:
        history_item["thoughts"] = thoughts
        _record_thought_history_item(state)
    history.append(history_item)
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    _append_chat_entry(round_number, _agent_label(agent_name), public_message)
    log_details = dict(
        round=round_number,
        agent=agent_name,
        message=discussion_message,
    )
    if thoughts:
        log_details["thoughts"] = thoughts
    log_event("public_discussion_message", **log_details)
    metrics.record_agent_turn()
    return llm_response


def record_tool_response_thoughts(callback_context, llm_response):
    """Keep high-condition tool-agent thoughts until the tool exchange is logged."""
    if not thought_history_enabled():
        return llm_response

    agent_name = getattr(callback_context, "agent_name", None)
    if not agent_name:
        return llm_response

    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    thoughts = _thought_text_from_parts(parts)
    if not thoughts:
        return llm_response

    state = _get_state(callback_context)
    thoughts_by_agent = dict(state.get(TOOL_RESPONSE_THOUGHTS_STATE_KEY, {}) or {})
    thoughts_by_agent[agent_name] = thoughts
    state[TOOL_RESPONSE_THOUGHTS_STATE_KEY] = thoughts_by_agent
    return llm_response


def _pop_tool_response_thoughts(ctx, callee_name: str | None) -> str:
    """Return and clear stashed thoughts for a just-finished tool response."""
    if not callee_name:
        return ""

    state = _get_state(ctx)
    thoughts_by_agent = dict(state.get(TOOL_RESPONSE_THOUGHTS_STATE_KEY, {}) or {})
    thoughts = str(thoughts_by_agent.pop(callee_name, "")).strip()
    state[TOOL_RESPONSE_THOUGHTS_STATE_KEY] = thoughts_by_agent
    return thoughts


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
    thoughts = (
        _pop_tool_response_thoughts(tool_context, callee_name)
        if thought_history_enabled()
        else ""
    )
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
    history_item = {
        "round": round_number,
        "agent": callee_key,
        "message": message,
        "source": "agent_tool_call",
        "caller": caller_key,
    }
    if thoughts:
        history_item["thoughts"] = thoughts
        _record_thought_history_item(state)
    history.append(history_item)
    state[PUBLIC_DISCUSSION_STATE_KEY] = history
    _append_chat_entry(
        round_number,
        f"Tool: {caller_label} -> {callee_label}",
        message,
    )
    log_details = dict(
        round=round_number,
        caller=caller_key,
        callee=callee_key,
        question=question,
        answer=answer,
        message=message,
    )
    if thoughts:
        log_details["thoughts"] = thoughts
    log_event("public_tool_exchange", **log_details)
    return None


def _indent_history_detail(text: str) -> str:
    """Indent multi-line history details under a bullet."""
    return "\n".join(f"  {line}" for line in text.strip().splitlines())


def _history_items_for_active_scope(history: list[object]) -> list[object]:
    """Return history entries visible under the active input-context condition."""
    scope = input_history_scope()
    if scope == "none":
        return []
    if scope != "current_round":
        return history

    current_round = _round_number()
    return [
        item
        for item in history
        if isinstance(item, dict) and item.get("round") == current_round
    ]


def build_public_discussion_history(ctx) -> str:
    """Format the stored public discussion transcript for inclusion in prompts."""
    if input_history_scope() == "none":
        return "- Discussion history is hidden for this input-context condition."

    state = _get_state(ctx)
    history = state.get(PUBLIC_DISCUSSION_STATE_KEY, [])
    if not isinstance(history, list) or not history:
        return "- No discussion contributions yet."

    lines = []
    include_thoughts = thought_history_enabled()
    for item in _history_items_for_active_scope(history):
        if not isinstance(item, dict):
            continue
        round_number = item.get("round", "?")
        agent = str(item.get("agent", "unknown_agent")).replace("_", " ").title()
        message = str(item.get("message", "")).strip()
        if message:
            thoughts = str(item.get("thoughts", "")).strip()
            if include_thoughts and thoughts:
                lines.append(
                    f"- Round {round_number}, {agent}:\n"
                    "  Model thoughts before public response:\n"
                    f"{_indent_history_detail(thoughts)}\n"
                    "  Public response:\n"
                    f"{_indent_history_detail(message)}"
                )
            else:
                lines.append(f"- Round {round_number}, {agent}: {message}")

    return "\n".join(lines) if lines else "- No discussion contributions yet."
