"""Memory update tools for persisting each discussion agent's mental model."""

import logging

from google.adk.tools.tool_context import ToolContext

from ..config.simulation_context import write_agent_memory
from ..config.metrics import metrics
from ..config.trace import log_event

logger = logging.getLogger(__name__)


def _set_agent_memory(tool_context: ToolContext, agent_key: str, memory: str) -> dict:
    """Persist a full memory replacement for the selected discussion agent."""
    metrics.record_agent_turn()
    if not memory or not memory.strip():
        logger.warning("Empty memory update for %s", agent_key)
        log_event(
            "memory_update_missing",
            agent=agent_key,
            round=metrics.loop_count + 1,
        )
        return {"status": "EMPTY_MEMORY", "agent": agent_key}

    write_agent_memory(agent_key, memory)
    log_event(
        "memory_updated",
        agent=agent_key,
        round=metrics.loop_count + 1,
    )
    return {"status": "MEMORY_UPDATED", "agent": agent_key}


def set_agent_1_memory(tool_context: ToolContext, memory: str) -> dict:
    """Persist Agent 1's updated memory."""
    return _set_agent_memory(tool_context, "agent_1", memory)


def set_agent_2_memory(tool_context: ToolContext, memory: str) -> dict:
    """Persist Agent 2's updated memory."""
    return _set_agent_memory(tool_context, "agent_2", memory)


def set_agent_3_memory(tool_context: ToolContext, memory: str) -> dict:
    """Persist Agent 3's updated memory."""
    return _set_agent_memory(tool_context, "agent_3", memory)


def set_agent_4_memory(tool_context: ToolContext, memory: str) -> dict:
    """Persist Agent 4's updated memory."""
    return _set_agent_memory(tool_context, "agent_4", memory)
