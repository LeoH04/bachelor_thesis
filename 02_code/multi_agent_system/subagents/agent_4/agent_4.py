from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)


def agent_4_instruction(_ctx) -> str:
    return build_agent_instruction("agent_4", _ctx)


def agent_4_tool_instruction(_ctx) -> str:
    return build_agent_tool_instruction("agent_4", _ctx)


agent_4 = LlmAgent(
    name="agent_4",
    model=DISCUSSION_MODEL,
    output_key="agent_4_response",
    instruction=agent_4_instruction,
    include_contents="none",
    after_model_callback=record_public_discussion_response,
)

agent_4_tool = LlmAgent(
    name="agent_4_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_4_tool_instruction,
    include_contents="none",
)
