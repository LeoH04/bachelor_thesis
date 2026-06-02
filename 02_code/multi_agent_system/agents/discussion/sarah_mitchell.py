"""Define Sarah Mitchell's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.history import (
    record_public_discussion_response,
    record_tool_response_thoughts,
    strip_adk_for_context,
)
from ...config.model import DISCUSSION_MODEL, TOOL_MODEL
from ...config.prompts import build_agent_instruction, build_agent_tool_instruction

SARAH_MITCHELL_SYSTEM_PROMPT = ()


def sarah_mitchell_instruction(_ctx) -> str:
    """Build Sarah Mitchell's prompt for its scheduled public discussion turn."""
    return build_agent_instruction(
        "sarah_mitchell",
        _ctx,
        SARAH_MITCHELL_SYSTEM_PROMPT,
    )


def sarah_mitchell_tool_instruction(_ctx) -> str:
    """Build Sarah Mitchell's prompt when called by another agent as a tool."""
    return build_agent_tool_instruction(
        "sarah_mitchell",
        _ctx,
        SARAH_MITCHELL_SYSTEM_PROMPT,
    )


sarah_mitchell = LlmAgent(
    name="sarah_mitchell",
    model=DISCUSSION_MODEL,
    output_key="sarah_mitchell_response",
    instruction=sarah_mitchell_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_public_discussion_response,
)

sarah_mitchell_tool = LlmAgent(
    name="sarah_mitchell_tool",
    model=TOOL_MODEL,
    instruction=sarah_mitchell_tool_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_tool_response_thoughts,
)
