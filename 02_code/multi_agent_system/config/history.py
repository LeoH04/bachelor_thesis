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
from .run_warnings import record_run_warning
from .task import AGENT_KEYS
from .trace import log_event

PUBLIC_DISCUSSION_STATE_KEY = "public_discussion_history"
_MALFORMED_HISTORY_WARNING_KEYS: set[tuple[object, ...]] = set()


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


def _preview(value: object, limit: int = 500) -> str:
    """Return a bounded text preview for warning details."""
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    return text[:limit]


def _record_malformed_history_warning(
    warning_key: tuple[object, ...],
    code: str,
    message: str,
    **details: object,
) -> None:
    """Record one malformed-history warning once per process."""
    if warning_key in _MALFORMED_HISTORY_WARNING_KEYS:
        return

    _MALFORMED_HISTORY_WARNING_KEYS.add(warning_key)
    record_run_warning(code, message, **details)


def reset_public_discussion_history(state: dict) -> None:
    """Clear the public discussion transcript stored in the simulation state."""
    if state is not None:
        state[PUBLIC_DISCUSSION_STATE_KEY] = []


def _append_chat_entry(round_number: int, speaker: str, message: str) -> None:
    """Append one public discussion entry to the human-readable chat markdown."""
    CHAT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHAT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"## Round {round_number} - {speaker}\n\n{message.strip()}\n\n")


def _part_has_tool_call(part: object) -> bool:
    """Return whether an ADK response part represents a tool interaction."""
    if isinstance(part, dict):
        return bool(part.get("function_call") or part.get("function_response"))

    return bool(
        getattr(part, "function_call", None)
        or getattr(part, "function_response", None)
    )


def record_public_discussion_response(callback_context, llm_response) -> None:
    """Append only a normal agent turn's visible final message to shared state."""
    agent_name = getattr(callback_context, "agent_name", None)
    if agent_name not in AGENT_KEYS:
        return None

    content = getattr(llm_response, "content", None)
    parts = list(getattr(content, "parts", None) or [])
    visible_parts = _drop_thought_parts(parts)
    text = _visible_text_from_parts(visible_parts)

    if any(_part_has_tool_call(part) for part in visible_parts):
        return llm_response

    if not METADATA_JSON_LABEL_RE.search(text):
        record_run_warning(
            "agent_output_missing_metadata",
            "Scheduled agent response was not recorded because METADATA_JSON is missing.",
            agent=agent_name,
            round=_round_number(),
            response_preview=_preview(text),
        )
        return llm_response

    public_message = _extract_public_message(text)
    if not public_message:
        record_run_warning(
            "agent_output_missing_public_message",
            "Scheduled agent response was not recorded because PUBLIC_MESSAGE is empty or missing.",
            agent=agent_name,
            round=_round_number(),
            response_preview=_preview(text),
        )
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
        record_run_warning(
            "tool_exchange_unrecorded",
            "Agent tool exchange could not be added to public history because no question or answer text was extracted.",
            round=_round_number(),
            caller=_agent_key(caller_name),
            callee=_agent_key(callee_name),
            args_preview=_preview(args),
            result_preview=_preview(result),
        )
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
    if not isinstance(history, list):
        _record_malformed_history_warning(
            ("history_not_list", _preview(history)),
            "public_history_malformed",
            "Public discussion history was ignored because it is not a list.",
            history_type=type(history).__name__,
            history_preview=_preview(history),
        )
        return "- No discussion contributions yet."

    lines = []
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            _record_malformed_history_warning(
                ("non_dict", index, _preview(item)),
                "public_history_item_malformed",
                "Public discussion history item was skipped because it is not a dictionary.",
                index=index,
                item_type=type(item).__name__,
                item_preview=_preview(item),
            )
            continue
        round_number = item.get("round", "?")
        agent = str(item.get("agent", "unknown_agent")).replace("_", " ").title()
        message = str(item.get("message", "")).strip()
        if message:
            lines.append(f"- Round {round_number}, {agent}: {message}")
        else:
            _record_malformed_history_warning(
                (
                    "empty_message",
                    index,
                    _preview(item.get("round")),
                    _preview(item.get("agent")),
                ),
                "public_history_item_missing_message",
                "Public discussion history item was skipped because its message is empty or missing.",
                index=index,
                round=round_number,
                agent=item.get("agent"),
                item_preview=_preview(item),
            )

    return "\n".join(lines) if lines else "- No discussion contributions yet."
