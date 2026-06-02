"""Define Emily Brooks's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.history import (
    record_public_discussion_response,
    record_tool_response_thoughts,
    strip_adk_for_context,
)
from ...config.model import DISCUSSION_MODEL, TOOL_MODEL
from ...config.prompts import build_agent_instruction, build_agent_tool_instruction

EMILY_BROOKS_SYSTEM_PROMPT = ()


def emily_brooks_instruction(_ctx) -> str:
    """Build Emily Brooks's prompt for its scheduled public discussion turn."""
    return build_agent_instruction(
        "emily_brooks",
        _ctx,
        EMILY_BROOKS_SYSTEM_PROMPT,
    )


def emily_brooks_tool_instruction(_ctx) -> str:
    """Build Emily Brooks's prompt when called by another agent as a tool."""
    return build_agent_tool_instruction(
        "emily_brooks",
        _ctx,
        EMILY_BROOKS_SYSTEM_PROMPT,
    )


emily_brooks = LlmAgent(
    name="emily_brooks",
    model=DISCUSSION_MODEL,
    output_key="emily_brooks_response",
    instruction=emily_brooks_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_public_discussion_response,
)

emily_brooks_tool = LlmAgent(
    name="emily_brooks_tool",
    model=TOOL_MODEL,
    instruction=emily_brooks_tool_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_tool_response_thoughts,
)
