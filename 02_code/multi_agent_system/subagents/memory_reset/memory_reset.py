import json
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...config.simulation_context import (
    reset_all_agent_memories,
    reset_public_discussion_history,
)
from ...config.trace import log_event


def reset_agent_memories(tool_context: ToolContext) -> dict:
    reset_all_agent_memories()
    reset_public_discussion_history(tool_context.state)
    log_event("memory_reset")
    return {"status": "MEMORY_RESET"}


class MemoryResetAgent(BaseAgent):
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        actions = EventActions()
        tool_context = ToolContext(ctx, event_actions=actions)
        result = reset_agent_memories(tool_context)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=actions,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=json.dumps(result))],
            ),
        )


memory_reset_agent = MemoryResetAgent(name="memory_reset")
