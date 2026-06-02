"""Define James Carter's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.history import (
    record_public_discussion_response,
    record_tool_response_thoughts,
    strip_adk_for_context,
)
from ...config.model import DISCUSSION_MODEL, TOOL_MODEL
from ...config.prompts import build_agent_instruction, build_agent_tool_instruction

JAMES_CARTER_SYSTEM_PROMPT = ()


def james_carter_instruction(_ctx) -> str:
    """Build James Carter's prompt for its scheduled public discussion turn."""
    return build_agent_instruction(
        "james_carter",
        _ctx,
        JAMES_CARTER_SYSTEM_PROMPT,
    )


def james_carter_tool_instruction(_ctx) -> str:
    """Build James Carter's prompt when called by another agent as a tool."""
    return build_agent_tool_instruction(
        "james_carter",
        _ctx,
        JAMES_CARTER_SYSTEM_PROMPT,
    )


james_carter = LlmAgent(
    name="james_carter",
    model=DISCUSSION_MODEL,
    output_key="james_carter_response",
    instruction=james_carter_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_public_discussion_response,
)

james_carter_tool = LlmAgent(
    name="james_carter_tool",
    model=TOOL_MODEL,
    instruction=james_carter_tool_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_tool_response_thoughts,
)
