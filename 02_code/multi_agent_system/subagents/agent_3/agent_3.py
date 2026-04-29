from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import build_agent_instruction


def agent_3_instruction(_ctx) -> str:
    return build_agent_instruction("agent_3")

agent_3 = LlmAgent(
    name="agent_3",
    model=DISCUSSION_MODEL,
    output_key="agent_3_response",
    instruction=agent_3_instruction,
)