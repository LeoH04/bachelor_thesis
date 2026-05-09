"""Collect and log aggregate metrics for a simulation run."""

import logging
import time

from .make_session_log import SESSION_LOG_FILE, update_run_metadata

# Configure file-based logging for metrics in the unified session log.
file_handler = logging.FileHandler(SESSION_LOG_FILE, mode="a")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

logger = logging.getLogger("metrics")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)


class MetricsTracker:
    """Track token usage, communication counts, decisions, and runtime."""

    def __init__(self):
        """Initialize counters and timing state for one simulation run."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.loop_count = 0
        self.agent_turn_count = 0
        self.agent_tool_call_count = 0
        self.memory_update_count = 0
        self.final_candidate = None
        self.final_decision_method = None
        self.final_vote_count = {}
        self.correct_candidate = None
        self.decision_correct = None
        self.start_time = time.time()
        self.end_time = None
        self._final_decision_recorded = False
        self._successful_completion_recorded = False
        self._finalized = False

    def add_tokens(self, input_tokens: int, output_tokens: int):
        """Record token usage"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        total = input_tokens + output_tokens
        logger.info(f"Tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total}")

    def record_loop(self):
        """Increment loop counter"""
        self.loop_count += 1
        logger.info(f"Loop {self.loop_count} completed")

    def record_agent_turn(self):
        """Record a main agent turn (excludes vote checker)."""
        self.agent_turn_count += 1
        logger.info(f"Agent turns: {self.agent_turn_count}")

    def record_agent_tool_call(self):
        """Record an agent-to-agent tool call."""
        self.agent_tool_call_count += 1
        logger.info(f"Agent tool calls: {self.agent_tool_call_count}")

    def record_memory_update(self):
        """Record a persisted agent memory update."""
        self.memory_update_count += 1
        logger.info(f"Memory updates: {self.memory_update_count}")

    def record_final_decision(
        self,
        candidate: str | None,
        method: str,
        vote_count: dict[str, int],
        correct_candidate: str | None = None,
    ) -> bool:
        """Record the final selected candidate once."""
        if self._final_decision_recorded:
            return False

        self._final_decision_recorded = True
        self.final_candidate = candidate
        self.final_decision_method = method
        self.final_vote_count = vote_count
        self.correct_candidate = correct_candidate
        if candidate is None:
            self.decision_correct = 0
        elif correct_candidate:
            self.decision_correct = 1 if candidate == correct_candidate else 0
        logger.info(f"Final Chosen Candidate: {candidate}")
        logger.info(f"Final Decision Method: {method}")
        logger.info(f"Final Vote Count: {vote_count}")
        if correct_candidate:
            logger.info(f"Correct Candidate: {correct_candidate}")
            logger.info(f"Decision Correct: {self.decision_correct}")
        update_run_metadata(
            {
                "final_candidate": self.final_candidate,
                "decision_method": self.final_decision_method,
                "vote_count": self.final_vote_count,
                "correct_candidate": self.correct_candidate,
                "decision_correct": self.decision_correct,
            }
        )
        return True

    def record_successful_completion(self) -> None:
        """Mark that final decision handling completed without downstream errors."""
        self._successful_completion_recorded = True

    def end_simulation(self):
        """End simulation and log summary"""
        if self._finalized:
            return  # Only run once
        
        self._finalized = True
        self.end_time = time.time()
        runtime = self.end_time - self.start_time
        
        logger.info("=" * 70)
        logger.info("SIMULATION METRICS")
        logger.info("=" * 70)
        logger.info(f"Total Loops: {self.loop_count}")
        agent_tool_messages = self.agent_tool_call_count * 2
        total_messages = self.agent_turn_count + agent_tool_messages
        logger.info(f"Agent Turns (no vote checker): {self.agent_turn_count}")
        logger.info(f"Agent Tool Calls: {self.agent_tool_call_count}")
        logger.info(f"Agent Tool Messages: {agent_tool_messages}")
        logger.info(f"Memory Updates: {self.memory_update_count}")
        logger.info(f"Total Messages (no vote checker): {total_messages}")
        logger.info(f"Input Tokens: {self.total_input_tokens}")
        logger.info(f"Output Tokens: {self.total_output_tokens}")
        logger.info(f"Total Tokens: {self.total_input_tokens + self.total_output_tokens}")
        final_candidate = self.final_candidate if self._final_decision_recorded else "(not recorded)"
        logger.info(f"Final Chosen Candidate: {final_candidate}")
        if self.final_decision_method:
            logger.info(f"Final Decision Method: {self.final_decision_method}")
            logger.info(f"Final Vote Count: {self.final_vote_count}")
        if self.correct_candidate:
            logger.info(f"Correct Candidate: {self.correct_candidate}")
            logger.info(f"Decision Correct: {self.decision_correct}")
        logger.info(f"Runtime: {runtime:.2f}s")
        logger.info("=" * 70)
        metadata_updates = {
            "status": "completed" if self._successful_completion_recorded else "failed",
            "rounds": self.loop_count,
            "agent_turns": self.agent_turn_count,
            "agent_tool_calls": self.agent_tool_call_count,
            "agent_tool_messages": agent_tool_messages,
            "memory_updates": self.memory_update_count,
            "total_messages": total_messages,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "final_candidate": self.final_candidate,
            "decision_method": self.final_decision_method,
            "vote_count": self.final_vote_count,
            "correct_candidate": self.correct_candidate,
            "decision_correct": self.decision_correct,
            "runtime_seconds": round(runtime, 4),
        }
        if self._successful_completion_recorded:
            metadata_updates["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        else:
            metadata_updates["failed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            metadata_updates["failure_reason"] = (
                "simulation_finalization_failed"
                if self._final_decision_recorded
                else "simulation_ended_without_final_decision"
            )

        update_run_metadata(metadata_updates)


metrics = MetricsTracker()
logger.info("Metrics tracker initialized")
