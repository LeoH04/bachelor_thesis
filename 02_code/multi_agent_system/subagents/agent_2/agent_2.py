from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import AGENT_2_INSTRUCTION

agent_2 = LlmAgent(
    name="agent_2",
    model=DISCUSSION_MODEL,
    output_key="agent_2_response",
    instruction=AGENT_2_INSTRUCTION,
)