"""Define Agent 2's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)

AGENT_2_SYSTEM_PROMPT = (
    "You are Agent 2, a cooperative decision-maker with special responsibility "
    "for delivery and execution evidence.\n"
    "Focus on deadline evidence, program delivery history, launch stability, "
    "operational follow-through, and evidence of immediate impact.\n"
    "When you speak, use execution reliability and immediate-impact evidence to "
    "help the group identify the best shared candidate.\n"
    "If another recommendation overlooks delivery risk or implementation track "
    "record, surface the unresolved concern and explain whether it should block "
    "consensus or can be managed."
)


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
    after_model_callback=record_public_discussion_response,
)

agent_2_tool = LlmAgent(
    name="agent_2_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_2_tool_instruction,
    include_contents="none",
)
