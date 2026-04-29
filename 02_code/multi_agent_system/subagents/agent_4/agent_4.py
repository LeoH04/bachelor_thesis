from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import build_agent_instruction


def agent_4_instruction(_ctx) -> str:
    return build_agent_instruction("agent_4")

agent_4 = LlmAgent(
    name="agent_4",
    model=DISCUSSION_MODEL,
    output_key="agent_4_response",
    instruction=agent_4_instruction,
)