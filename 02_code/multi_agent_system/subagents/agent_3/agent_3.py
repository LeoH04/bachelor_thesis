from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import AGENT_3_INSTRUCTION

agent_3 = LlmAgent(
    name="agent_3",
    model=DISCUSSION_MODEL,
    output_key="agent_3_response",
    instruction=AGENT_3_INSTRUCTION,
)