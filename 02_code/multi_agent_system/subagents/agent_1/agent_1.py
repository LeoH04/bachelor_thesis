from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import build_agent_instruction


def agent_1_instruction(_ctx) -> str:
    return build_agent_instruction("agent_1")

agent_1 = LlmAgent(
    name="agent_1",
    model=DISCUSSION_MODEL,
    output_key="agent_1_response",
    instruction=agent_1_instruction,
)