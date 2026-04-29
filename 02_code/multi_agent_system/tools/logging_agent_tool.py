from __future__ import annotations

from typing import Any

from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext

from ..config.metrics import metrics
from ..config.trace import _truncate_text, log_event


def _preview(value: Any, limit: int = 500) -> str:
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    return _truncate_text(text, limit)


class LoggingAgentTool(AgentTool):
    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        metrics.record_agent_tool_call()
        caller = None
        if hasattr(tool_context, "_invocation_context"):
            caller = tool_context._invocation_context.agent.name

        log_event(
            "agent_tool_call_start",
            caller=caller,
            callee=self.agent.name,
            function_call_id=tool_context.function_call_id,
            args_preview=_preview(args),
        )

        result = await super().run_async(args=args, tool_context=tool_context)

        log_event(
            "agent_tool_call_end",
            caller=caller,
            callee=self.agent.name,
            function_call_id=tool_context.function_call_id,
            result_preview=_preview(result),
        )

        return result
