"""Check end-of-round votes and stop the discussion when a decision is reached."""

import json
import re
from collections.abc import AsyncGenerator
from collections import Counter

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...config.metrics import metrics
from ...config.simulation_context import archive_agent_memories, get_correct_candidate
from ...config.trace import log_event

MAX_DISCUSSION_ROUNDS = 5


def _record_final_decision(
    candidate: str,
    method: str,
    vote_count: dict[str, int],
) -> None:
    """Persist and trace the first final decision selected by the simulation."""
    correct_candidate = get_correct_candidate()
    decision_recorded = metrics.record_final_decision(
        candidate=candidate,
        method=method,
        vote_count=vote_count,
        correct_candidate=correct_candidate,
    )
    if decision_recorded:
        archive_dir = archive_agent_memories()
        if archive_dir is not None:
            log_event(
                "agent_memories_archived",
                directory=str(archive_dir),
                round=metrics.loop_count,
            )
        log_event(
            "final_decision",
            candidate=candidate,
            method=method,
            vote_count=vote_count,
            correct_candidate=correct_candidate,
            decision_correct=metrics.decision_correct,
            round=metrics.loop_count,
        )


# --- metrics tool ---
def record_metrics(tool_context: ToolContext) -> dict:
    """Record metrics for current execution - increment loop counter
    
    Note: Token tracking is handled via runtime usage events.
    """
    # Increment loop counter
    metrics.record_loop()
    
    return {"status": "metrics_recorded", "loop": metrics.loop_count}


# --- vote extraction ---
def extract_vote(text: str) -> str | None:
    """Extract a valid candidate vote from an agent's metadata JSON block."""
    match = re.search(r"METADATA_JSON:\s*(\{.*?\})", text, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        vote = data.get("vote")
        return vote if vote in {"Alice", "Bob", "Carol", "Eve", "Dave"} else None
    except json.JSONDecodeError:
        return None


# --- consensus tool ---
def check_consensus(tool_context: ToolContext) -> dict:
    """Count current agent votes and return whether the loop should continue."""
    votes = []

    for i in range(1, 5):
        response = tool_context.state.get(f"agent_{i}_response", "")
        vote = extract_vote(response)
        if vote:
            votes.append(vote)

    counts = Counter(votes)

    if counts:
        winner, count = counts.most_common(1)[0]
        vote_count = dict(counts)
        if count >= 4:
            _record_final_decision(winner, "consensus", vote_count)
            tool_context.actions.escalate = True
            return {
                "status": "CONSENSUS_REACHED",
                "winner": winner,
                "vote_count": vote_count,
            }

        if metrics.loop_count >= MAX_DISCUSSION_ROUNDS:
            _record_final_decision(winner, "max_round_majority_vote", vote_count)
            tool_context.actions.escalate = True
            return {
                "status": "MAX_ROUNDS_REACHED",
                "winner": winner,
                "vote_count": vote_count,
            }

    return {
        "status": "CONTINUE_DISCUSSION",
        "vote_count": dict(counts),
    }


class VoteCheckerAgent(BaseAgent):
    """ADK workflow agent that records round metrics and checks consensus."""

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """Run the vote check and emit the result as an ADK event."""
        actions = EventActions()
        tool_context = ToolContext(ctx, event_actions=actions)

        record_metrics(tool_context)
        result = check_consensus(tool_context)

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


vote_checker = VoteCheckerAgent(name="vote_checker")
