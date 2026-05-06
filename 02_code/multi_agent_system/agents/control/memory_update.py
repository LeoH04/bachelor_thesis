"""Passive memory-update agents that run after each public discussion message."""

from google.adk.agents import LlmAgent, ParallelAgent

from ...config.memory import record_memory_update_response
from ...config.model import DISCUSSION_MODEL
from ...config.prompts import build_memory_update_instruction
from ...config.task import AGENT_KEYS


def _make_memory_update_agent(agent_key: str, after_agent_key: str) -> LlmAgent:
    """Create one passive updater for one agent's markdown memory."""

    def instruction(
        ctx,
        target_agent_key=agent_key,
        latest_speaker_key=after_agent_key,
    ) -> str:
        return build_memory_update_instruction(
            target_agent_key,
            ctx,
            latest_speaker_key=latest_speaker_key,
        )

    def after_model_callback(callback_context, llm_response, target_agent_key=agent_key):
        return record_memory_update_response(
            target_agent_key,
            callback_context,
            llm_response,
        )

    return LlmAgent(
        name=f"{agent_key}_memory_update_after_{after_agent_key}",
        model=DISCUSSION_MODEL,
        instruction=instruction,
        include_contents="none",
        after_model_callback=after_model_callback,
    )


def make_memory_update_stage(after_agent_key: str) -> ParallelAgent:
    """Create the parallel stage that updates all memories after one public message."""
    return ParallelAgent(
        name=f"memory_update_after_{after_agent_key}",
        sub_agents=[
            _make_memory_update_agent(agent_key, after_agent_key)
            for agent_key in AGENT_KEYS
        ],
    )

MEMORY_UPDATE_STAGES = {
    agent_key: make_memory_update_stage(agent_key)
    for agent_key in AGENT_KEYS
}
