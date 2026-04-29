from google.adk.agents import LoopAgent, SequentialAgent

from .config.metrics import metrics
from .subagents.agent_1.agent_1 import agent_1
from .subagents.agent_2.agent_2 import agent_2
from .subagents.agent_3.agent_3 import agent_3
from .subagents.agent_4.agent_4 import agent_4
from .subagents.vote_checker.vote_checker import vote_checker

discussion_round = SequentialAgent(
    name="discussion_round",
    sub_agents=[
        agent_1,
        agent_2,
        agent_3,
        agent_4,
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