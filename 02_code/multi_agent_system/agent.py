from google.adk.agents import LoopAgent, SequentialAgent

from .config.metrics import metrics
from .config.simulation_context import archive_agent_memories
from .config.trace import log_event
from .agents.control.memory_reset import memory_reset_agent
from .agents.control.memory_update import (
    memory_update_after_agent_1,
    memory_update_after_agent_2,
    memory_update_after_agent_3,
    memory_update_after_agent_4,
)
from .agents.control.vote_checker import MAX_DISCUSSION_ROUNDS, vote_checker
from .agents.discussion.agent_1 import agent_1, agent_1_tool
from .agents.discussion.agent_2 import agent_2, agent_2_tool
from .agents.discussion.agent_3 import agent_3, agent_3_tool
from .agents.discussion.agent_4 import agent_4, agent_4_tool
from .tools.logging_agent_tool import LoggingAgentTool

import atexit


def _wire_agent_tools() -> None:
    agent_1.tools = [
        LoggingAgentTool(agent=agent_2_tool),
        LoggingAgentTool(agent=agent_3_tool),
        LoggingAgentTool(agent=agent_4_tool),
    ]
    agent_2.tools = [
        LoggingAgentTool(agent=agent_1_tool),
        LoggingAgentTool(agent=agent_3_tool),
        LoggingAgentTool(agent=agent_4_tool),
    ]
    agent_3.tools = [
        LoggingAgentTool(agent=agent_1_tool),
        LoggingAgentTool(agent=agent_2_tool),
        LoggingAgentTool(agent=agent_4_tool),
    ]
    agent_4.tools = [
        LoggingAgentTool(agent=agent_1_tool),
        LoggingAgentTool(agent=agent_2_tool),
        LoggingAgentTool(agent=agent_3_tool),
    ]


_wire_agent_tools()

discussion_round = SequentialAgent(
    name="discussion_round",
    sub_agents=[
        agent_1,
        memory_update_after_agent_1,
        agent_2,
        memory_update_after_agent_2,
        agent_3,
        memory_update_after_agent_3,
        agent_4,
        memory_update_after_agent_4,
        vote_checker,
    ],
)

discussion_loop = LoopAgent(
    name="discussion_loop",
    max_iterations=MAX_DISCUSSION_ROUNDS,
    sub_agents=[discussion_round],
)

root_agent = SequentialAgent(
    name="simulation",
    sub_agents=[
        memory_reset_agent,
        discussion_loop,
    ],
)

# Register cleanup on module exit

def cleanup():
    if metrics.loop_count or metrics.agent_turn_count or metrics.final_candidate:
        archive_dir = archive_agent_memories()
        if archive_dir is not None:
            log_event("agent_memories_archived", directory=str(archive_dir))
    metrics.end_simulation()

atexit.register(cleanup)
