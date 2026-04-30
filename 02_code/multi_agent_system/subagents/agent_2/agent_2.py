from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)


def agent_2_instruction(_ctx) -> str:
    return build_agent_instruction("agent_2", _ctx)


def agent_2_tool_instruction(_ctx) -> str:
    return build_agent_tool_instruction("agent_2", _ctx)


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
