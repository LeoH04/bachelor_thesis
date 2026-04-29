from google.adk.agents import LlmAgent

from ...config.model import DISCUSSION_MODEL
from ...config.instruction import AGENT_1_INSTRUCTION

agent_1 = LlmAgent(
    name="agent_1",
    model=DISCUSSION_MODEL,
    output_key="agent_1_response",
    instruction=AGENT_1_INSTRUCTION,
)