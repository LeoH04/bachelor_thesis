import logging

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

from ...config.instruction import extract_memory_block, write_agent_memory
from ...config.metrics import metrics
from ...config.trace import log_event
from ...config.model import VOTE_MODEL

logger = logging.getLogger(__name__)


def _update_agent_memory(tool_context: ToolContext, agent_key: str) -> dict:
    metrics.record_agent_turn()
    response_key = f"{agent_key}_response"
    response = tool_context.state.get(response_key, "")
    memory_block = extract_memory_block(response)

    if not memory_block:
        logger.warning("No memory block found for %s", agent_key)
        log_event(
            "memory_update_missing",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        return {"status": "NO_MEMORY_BLOCK", "agent": agent_key}

    write_agent_memory(agent_key, memory_block)
    log_event(
        "memory_updated",
        agent=agent_key,
        round=metrics.loop_count + 1,
    )
    return {"status": "MEMORY_UPDATED", "agent": agent_key}


def update_agent_1_memory(tool_context: ToolContext) -> dict:
    return _update_agent_memory(tool_context, "agent_1")


def update_agent_2_memory(tool_context: ToolContext) -> dict:
    return _update_agent_memory(tool_context, "agent_2")


def update_agent_3_memory(tool_context: ToolContext) -> dict:
    return _update_agent_memory(tool_context, "agent_3")


def update_agent_4_memory(tool_context: ToolContext) -> dict:
    return _update_agent_memory(tool_context, "agent_4")


memory_update_agent_1 = LlmAgent(
    name="memory_update_agent_1",
    model=VOTE_MODEL,
    tools=[update_agent_1_memory],
    instruction="""
Call the update_agent_1_memory tool and report only the tool result.
""",
)

memory_update_agent_2 = LlmAgent(
    name="memory_update_agent_2",
    model=VOTE_MODEL,
    tools=[update_agent_2_memory],
    instruction="""
Call the update_agent_2_memory tool and report only the tool result.
""",
)

memory_update_agent_3 = LlmAgent(
    name="memory_update_agent_3",
    model=VOTE_MODEL,
    tools=[update_agent_3_memory],
    instruction="""
Call the update_agent_3_memory tool and report only the tool result.
""",
)

memory_update_agent_4 = LlmAgent(
    name="memory_update_agent_4",
    model=VOTE_MODEL,
    tools=[update_agent_4_memory],
    instruction="""
Call the update_agent_4_memory tool and report only the tool result.
""",
)
