from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)


def agent_1_instruction(_ctx) -> str:
    return build_agent_instruction("agent_1", _ctx)


def agent_1_tool_instruction(_ctx) -> str:
    return build_agent_tool_instruction("agent_1", _ctx)


agent_1 = LlmAgent(
    name="agent_1",
    model=DISCUSSION_MODEL,
    output_key="agent_1_response",
    instruction=agent_1_instruction,
    include_contents="none",
    after_model_callback=record_public_discussion_response,
)

agent_1_tool = LlmAgent(
    name="agent_1_tool",
    model=DISCUSSION_MODEL,
    instruction=agent_1_tool_instruction,
    include_contents="none",
)
