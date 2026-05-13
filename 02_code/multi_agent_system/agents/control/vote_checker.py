"""Check end-of-round votes and stop the discussion when a decision is reached."""

import json
from collections.abc import AsyncGenerator
from collections import Counter

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...config.memory import archive_agent_memories
from ...config.metrics import metrics
from ...config.response_text import VoteParseResult, parse_vote_from_response
from ...config.run_warnings import record_run_warning
from ...config.task import AGENT_KEYS, get_correct_candidate
from ...config.trace import log_event

MIN_CONSENSUS_ROUNDS = 2
MAX_DISCUSSION_ROUNDS = 5


def _vote_warning_code(parse_result: VoteParseResult) -> str:
    """Return the run-warning code to use for a failed vote parse."""
    if parse_result.error_code == "agent_output_missing_metadata":
        return "vote_missing"
    return parse_result.error_code or "vote_missing"


def _record_vote_warning(
    agent_key: str,
    parse_result: VoteParseResult,
    response: object,
) -> None:
    """Record why one agent did not contribute a valid vote."""
    code = _vote_warning_code(parse_result)
    record_run_warning(
        code,
        "Agent response did not contain a valid vote for consensus checking.",
        agent=agent_key,
        round=metrics.loop_count,
        parse_error_code=parse_result.error_code,
        parse_error_message=parse_result.error_message,
        metadata=parse_result.metadata,
        response_present=bool(response),
    )


def _collect_round_votes(tool_context: ToolContext) -> tuple[list[str], int, int]:
    """Return candidate votes, abstentions, and invalid/missing vote count."""
    votes = []
    abstention_count = 0
    invalid_or_missing_count = 0
    for agent_key in AGENT_KEYS:
        response = tool_context.state.get(f"{agent_key}_response", "")
        parse_result = parse_vote_from_response(response)
        if parse_result.vote:
            votes.append(parse_result.vote)
        elif parse_result.abstained:
            abstention_count += 1
        else:
            invalid_or_missing_count += 1
            _record_vote_warning(agent_key, parse_result, response)
    return votes, abstention_count, invalid_or_missing_count


def _warn_if_max_round_partial_votes(
    votes: list[str],
    vote_count: dict[str, int],
    abstention_count: int,
    invalid_or_missing_count: int,
) -> None:
    """Warn when max-round decision logic ignores malformed or missing votes."""
    if metrics.loop_count >= MAX_DISCUSSION_ROUNDS and invalid_or_missing_count:
        record_run_warning(
            "max_round_partial_valid_votes",
            "Maximum-round decision check used fewer valid votes than configured agents.",
            round=metrics.loop_count,
            valid_vote_count=len(votes),
            abstention_count=abstention_count,
            expected_vote_count=len(AGENT_KEYS),
            missing_or_invalid_vote_count=invalid_or_missing_count,
            vote_count=vote_count,
        )


def _record_final_decision(
    candidate: str | None,
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
        metrics.record_successful_completion()


def record_metrics(tool_context: ToolContext) -> dict:
    """Record metrics for current execution - increment loop counter
    
    Note: Token tracking is handled via runtime usage events.
    """
    # Increment loop counter
    metrics.record_loop()
    
    return {"status": "metrics_recorded", "loop": metrics.loop_count}


def check_consensus(tool_context: ToolContext) -> dict:
    """Count current agent votes and return whether the loop should continue."""
    votes, abstention_count, invalid_or_missing_count = _collect_round_votes(
        tool_context
    )

    counts = Counter(votes)

    vote_count = dict(counts)
    agent_count = len(AGENT_KEYS)
    majority_threshold = agent_count // 2 + 1
    _warn_if_max_round_partial_votes(
        votes,
        vote_count,
        abstention_count,
        invalid_or_missing_count,
    )

    if counts:
        winner, count = counts.most_common(1)[0]
        if count >= agent_count and metrics.loop_count >= MIN_CONSENSUS_ROUNDS:
            _record_final_decision(winner, "consensus", vote_count)
            tool_context.actions.escalate = True
            return {
                "status": "CONSENSUS_REACHED",
                "winner": winner,
                "vote_count": vote_count,
                "abstention_count": abstention_count,
            }

        if (
            metrics.loop_count >= MAX_DISCUSSION_ROUNDS
            and count >= majority_threshold
        ):
            _record_final_decision(winner, "max_round_majority_vote", vote_count)
            tool_context.actions.escalate = True
            return {
                "status": "MAX_ROUNDS_REACHED",
                "winner": winner,
                "vote_count": vote_count,
                "abstention_count": abstention_count,
            }

    if metrics.loop_count >= MAX_DISCUSSION_ROUNDS:
        _record_final_decision(None, "max_round_no_majority", vote_count)
        tool_context.actions.escalate = True
        return {
            "status": "MAX_ROUNDS_REACHED_NO_MAJORITY",
            "winner": None,
            "vote_count": vote_count,
            "abstention_count": abstention_count,
        }

    return {
        "status": "CONTINUE_DISCUSSION",
        "vote_count": vote_count,
        "abstention_count": abstention_count,
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
