from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import AGENT_4_INSTRUCTION

agent_4 = LlmAgent(
    name="agent_4",
    model=DISCUSSION_MODEL,
    output_key="agent_4_response",
    instruction=AGENT_4_INSTRUCTION,
)