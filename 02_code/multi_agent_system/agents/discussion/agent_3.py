"""Define Agent 3's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.history import (
    record_public_discussion_response,
    record_tool_response_thoughts,
)
from ...config.model import DISCUSSION_MODEL
from ...config.prompts import build_agent_instruction, build_agent_tool_instruction
from ...config.response_text import strip_adk_for_context

AGENT_3_SYSTEM_PROMPT = ()


def agent_3_instruction(_ctx) -> str:
    """Build Agent 3's prompt for its scheduled public discussion turn."""
    return build_agent_instruction("agent_3", _ctx, AGENT_3_SYSTEM_PROMPT)


def agent_3_tool_instruction(_ctx) -> str:
    """Build Agent 3's prompt when it is called by another agent as a tool."""
    return build_agent_tool_instruction("agent_3", _ctx, AGENT_3_SYSTEM_PROMPT)


agent_3 = LlmAgent(
    name="agent_3",
    model=DISCUSSION_MODEL,
    output_key="agent_3_response",
    instruction=agent_3_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_public_discussion_response,
)

agent_3_tool = LlmAgent(
    name="agent_3_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_3_tool_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_tool_response_thoughts,
)
