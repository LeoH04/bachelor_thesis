from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)


def agent_3_instruction(_ctx) -> str:
    return build_agent_instruction("agent_3", _ctx)


def agent_3_tool_instruction(_ctx) -> str:
    return build_agent_tool_instruction("agent_3", _ctx)


agent_3 = LlmAgent(
    name="agent_3",
    model=DISCUSSION_MODEL,
    output_key="agent_3_response",
    instruction=agent_3_instruction,
    include_contents="none",
    after_model_callback=record_public_discussion_response,
)

agent_3_tool = LlmAgent(
    name="agent_3_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_3_tool_instruction,
    include_contents="none",
)
