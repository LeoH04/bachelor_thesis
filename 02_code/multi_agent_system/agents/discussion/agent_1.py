"""Define Agent 1's scheduled discussion and tool-response LLM agents."""

from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.simulation_context import (
    build_agent_instruction,
    build_agent_tool_instruction,
    record_public_discussion_response,
)

AGENT_1_SYSTEM_PROMPT = (
    "You are Agent 1, the technical reliability evaluator.\n"
    "Focus on architecture risks, technical interview evidence, scaling tradeoffs, "
    "and each candidate's ability to detect reliability-critical flaws.\n"
    "When you speak, compare candidates through the lens of technical excellence "
    "and operational reliability.\n"
    "If another agent's recommendation underweights technical risk, state the "
    "disagreement clearly and ask targeted follow-up questions when useful."
)


def agent_1_instruction(_ctx) -> str:
    """Build Agent 1's prompt for its scheduled public discussion turn."""
    return build_agent_instruction("agent_1", _ctx, AGENT_1_SYSTEM_PROMPT)


def agent_1_tool_instruction(_ctx) -> str:
    """Build Agent 1's prompt when it is called by another agent as a tool."""
    return build_agent_tool_instruction("agent_1", _ctx, AGENT_1_SYSTEM_PROMPT)


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
