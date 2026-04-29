import logging

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

from ...config.instruction import reset_all_agent_memories
from ...config.model import VOTE_MODEL
from ...config.trace import log_event

logger = logging.getLogger(__name__)


def reset_agent_memories(tool_context: ToolContext) -> dict:
    reset_all_agent_memories()
    log_event("memory_reset")
    return {"status": "MEMORY_RESET"}


memory_reset_agent = LlmAgent(
    name="memory_reset",
    model=VOTE_MODEL,
    tools=[reset_agent_memories],
    instruction="""
Call the reset_agent_memories tool and report only the tool result.
""",
)
