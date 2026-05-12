"""Define Agent 2's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.history import record_public_discussion_response
from ...config.model import DISCUSSION_MODEL
from ...config.prompts import build_agent_instruction, build_agent_tool_instruction
from ...config.response_text import strip_adk_for_context

AGENT_2_SYSTEM_PROMPT = ()


def agent_2_instruction(_ctx) -> str:
    """Build Agent 2's prompt for its scheduled public discussion turn."""
    return build_agent_instruction("agent_2", _ctx, AGENT_2_SYSTEM_PROMPT)


def agent_2_tool_instruction(_ctx) -> str:
    """Build Agent 2's prompt when it is called by another agent as a tool."""
    return build_agent_tool_instruction("agent_2", _ctx, AGENT_2_SYSTEM_PROMPT)


agent_2 = LlmAgent(
    name="agent_2",
    model=DISCUSSION_MODEL,
    output_key="agent_2_response",
    instruction=agent_2_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
    after_model_callback=record_public_discussion_response,
)

agent_2_tool = LlmAgent(
    name="agent_2_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_2_tool_instruction,
    include_contents="none",
    before_model_callback=strip_adk_for_context,
)
