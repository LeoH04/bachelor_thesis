import json
import re
import logging
from collections import Counter

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

from ...config.model import VOTE_MODEL
from ...config.metrics import metrics

logger = logging.getLogger(__name__)


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
    votes = []

    for i in range(1, 5):
        response = tool_context.state.get(f"agent_{i}_response", "")
        vote = extract_vote(response)
        if vote:
            votes.append(vote)

    counts = Counter(votes)

    if counts:
        winner, count = counts.most_common(1)[0]
        if count >= 3:
            tool_context.actions.escalate = True
            return {
                "status": "CONSENSUS_REACHED",
                "winner": winner,
                "vote_count": dict(counts),
            }

    return {
        "status": "CONTINUE_DISCUSSION",
        "vote_count": dict(counts),
    }


# --- vote checker agent ---
vote_checker = LlmAgent(
    name="vote_checker",
    model=VOTE_MODEL,
    tools=[check_consensus, record_metrics],
    instruction="""
First, call the record_metrics tool to record loop metrics.

Then call the check_consensus tool.

Then report only the tool result.

If status is CONSENSUS_REACHED:
- Announce the winner clearly.

If status is CONTINUE_DISCUSSION:
- Briefly summarize the vote count.
""",
)