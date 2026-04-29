from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import build_agent_instruction


def agent_2_instruction(_ctx) -> str:
    return build_agent_instruction("agent_2")

agent_2 = LlmAgent(
    name="agent_2",
    model=DISCUSSION_MODEL,
    output_key="agent_2_response",
    instruction=agent_2_instruction,
)