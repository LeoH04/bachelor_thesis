from google.adk.agents import LoopAgent, SequentialAgent

from .config.metrics import metrics
from .subagents.agent_1.agent_1 import agent_1
from .subagents.agent_2.agent_2 import agent_2
from .subagents.agent_3.agent_3 import agent_3
from .subagents.agent_4.agent_4 import agent_4
from .subagents.memory_updater.memory_updater import (
    memory_update_agent_1,
    memory_update_agent_2,
    memory_update_agent_3,
    memory_update_agent_4,
)
from .subagents.memory_reset.memory_reset import memory_reset_agent
from .subagents.vote_checker.vote_checker import vote_checker
from .tools.logging_agent_tool import LoggingAgentTool


def _wire_agent_tools() -> None:
    agent_1.tools = [
        LoggingAgentTool(agent=agent_2),
        LoggingAgentTool(agent=agent_3),
        LoggingAgentTool(agent=agent_4),
    ]
    agent_2.tools = [
        LoggingAgentTool(agent=agent_1),
        LoggingAgentTool(agent=agent_3),
        LoggingAgentTool(agent=agent_4),
    ]
    agent_3.tools = [
        LoggingAgentTool(agent=agent_1),
        LoggingAgentTool(agent=agent_2),
        LoggingAgentTool(agent=agent_4),
    ]
    agent_4.tools = [
        LoggingAgentTool(agent=agent_1),
        LoggingAgentTool(agent=agent_2),
        LoggingAgentTool(agent=agent_3),
    ]


_wire_agent_tools()

discussion_round = SequentialAgent(
    name="discussion_round",
    sub_agents=[
        memory_reset_agent,
        agent_1,
        memory_update_agent_1,
        agent_2,
        memory_update_agent_2,
        agent_3,
        memory_update_agent_3,
        agent_4,
        memory_update_agent_4,
        vote_checker,
    ],
)

root_agent = LoopAgent(
    name="discussion_loop",
    max_iterations=15,
    sub_agents=[discussion_round],
)

# Register cleanup on module exit
import atexit

def cleanup():
    metrics.end_simulation()

atexit.register(cleanup)