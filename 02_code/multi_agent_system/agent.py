import atexit
import random
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.utils.context_utils import Aclosing

from .agents.control.memory_reset import memory_reset_agent
from .agents.control.memory_update import MEMORY_UPDATE_STAGES
from .agents.control.vote_checker import MAX_DISCUSSION_ROUNDS, vote_checker
from .agents.discussion.agent_1 import agent_1, agent_1_tool
from .agents.discussion.agent_2 import agent_2, agent_2_tool
from .agents.discussion.agent_3 import agent_3, agent_3_tool
from .config.memory import archive_agent_memories
from .config.metrics import metrics
from .config.smm import explicit_smm_memory_enabled
from .config.task import AGENT_KEYS
from .config.trace import log_event
from .tools.logging_agent_tool import LoggingAgentTool

EXPLICIT_SMM_MEMORY = explicit_smm_memory_enabled()

DISCUSSION_AGENTS = {
    "agent_1": agent_1,
    "agent_2": agent_2,
    "agent_3": agent_3,
}

TOOL_AGENTS = {
    "agent_1": agent_1_tool,
    "agent_2": agent_2_tool,
    "agent_3": agent_3_tool,
}


def _active_agent_items(agents: dict):
    missing_agent_keys = [
        agent_key for agent_key in AGENT_KEYS if agent_key not in agents
    ]
    if missing_agent_keys:
        raise ValueError(f"No discussion agent configured for {missing_agent_keys}")
    return [(agent_key, agents[agent_key]) for agent_key in AGENT_KEYS]


ACTIVE_DISCUSSION_AGENTS = _active_agent_items(DISCUSSION_AGENTS)
ACTIVE_TOOL_AGENTS = _active_agent_items(TOOL_AGENTS)


def _wire_agent_tools() -> None:
    for agent_key, agent in ACTIVE_DISCUSSION_AGENTS:
        agent.tools = [
            LoggingAgentTool(agent=tool_agent)
            for tool_agent_key, tool_agent in ACTIVE_TOOL_AGENTS
            if tool_agent_key != agent_key
        ]


_wire_agent_tools()


def _speaker_update_pairs() -> list[tuple[BaseAgent, BaseAgent]]:
    return [
        (speaker, MEMORY_UPDATE_STAGES[agent_key])
        for agent_key, speaker in ACTIVE_DISCUSSION_AGENTS
    ]


def _discussion_round_sub_agents() -> list[BaseAgent]:
    """Return the sub-agents used by one discussion round."""
    if EXPLICIT_SMM_MEMORY:
        return [
            sub_agent
            for speaker, memory_update in _speaker_update_pairs()
            for sub_agent in (speaker, memory_update)
        ] + [vote_checker]

    return [speaker for speaker, _ in _speaker_update_pairs()] + [vote_checker]


class RandomizedDiscussionRoundAgent(BaseAgent):
    """Run one discussion round with a freshly shuffled speaker order."""

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        speaker_update_pairs = _speaker_update_pairs()
        random.shuffle(speaker_update_pairs)
        log_event(
            "discussion_order",
            round=metrics.loop_count + 1,
            order=[speaker.name for speaker, _ in speaker_update_pairs],
        )

        for speaker, memory_update in speaker_update_pairs:
            sub_agents = (
                (speaker, memory_update)
                if EXPLICIT_SMM_MEMORY
                else (speaker,)
            )
            for sub_agent in sub_agents:
                async with Aclosing(sub_agent.run_async(ctx)) as agen:
                    async for event in agen:
                        yield event
                        if event.actions.escalate or ctx.should_pause_invocation(event):
                            return

        async with Aclosing(vote_checker.run_async(ctx)) as agen:
            async for event in agen:
                yield event


discussion_round = RandomizedDiscussionRoundAgent(
    name="discussion_round",
    sub_agents=_discussion_round_sub_agents(),
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
    try:
        if metrics.loop_count or metrics.agent_turn_count or metrics.final_candidate:
            archive_dir = archive_agent_memories()
            if archive_dir is not None:
                log_event("agent_memories_archived", directory=str(archive_dir))
    except Exception as exc:
        try:
            log_event("agent_memories_archive_failed", error=str(exc))
        except Exception:
            pass
    metrics.end_simulation()

atexit.register(cleanup)
