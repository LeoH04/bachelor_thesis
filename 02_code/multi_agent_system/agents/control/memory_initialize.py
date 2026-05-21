"""Initialize agent memories and public discussion state at simulation startup."""

import json
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...config.history import reset_public_discussion_history
from ...config.memory import initialize_all_agent_memories
from ...config.trace import log_event


def initialize_agent_memories(tool_context: ToolContext) -> dict:
    """Initialize run-local agent memories and clear the shared discussion history."""
    initialize_all_agent_memories()
    reset_public_discussion_history(tool_context.state)
    log_event("memory_initialized")
    return {"status": "MEMORY_INITIALIZED"}


class MemoryInitializationAgent(BaseAgent):
    """ADK workflow agent that performs the simulation initialization step."""

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """Run the initialization logic and emit a structured ADK event."""
        actions = EventActions()
        tool_context = ToolContext(ctx, event_actions=actions)
        result = initialize_agent_memories(tool_context)

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


memory_initialization_agent = MemoryInitializationAgent(name="memory_initialization")
