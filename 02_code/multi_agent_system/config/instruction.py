import json
from pathlib import Path

TASK_PATH = Path(__file__).parent / "hidden_profile_task.json"


def load_task():
    with TASK_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


TASK = load_task()


def build_information(agent_key: str) -> str:
    public = [f"Public: {x}" for x in TASK["public_information"]]
    private = [f"Private: {x}" for x in TASK["private_information"].get(agent_key, [])]
    return "\n".join(public + private)


INFORMATION_AGENT_1 = build_information("agent_1")
INFORMATION_AGENT_2 = build_information("agent_2")
INFORMATION_AGENT_3 = build_information("agent_3")
INFORMATION_AGENT_4 = build_information("agent_4")

AGENT_1_INSTRUCTION = f"""
You are Agent 1. You have the following information:
{INFORMATION_AGENT_1}

Read the discussion so far.
Give a short opinion.

End with this exact metadata format:

METADATA_JSON:
{{"agent": "agent_1", "vote": "<Alice|Bob|Carol|Eve|Dave>"}}
"""

AGENT_2_INSTRUCTION = f"""
You are Agent 2. You have the following information:
{INFORMATION_AGENT_2}

Read the discussion so far.
Give a short opinion.

End with this exact metadata format:

METADATA_JSON:
{{"agent": "agent_2", "vote": "<Alice|Bob|Carol|Eve|Dave>"}}
"""

AGENT_3_INSTRUCTION = f"""
You are Agent 3. You have the following information:
{INFORMATION_AGENT_3}

Read the discussion so far.
Give a short opinion.

End with this exact metadata format:

METADATA_JSON:
{{"agent": "agent_3", "vote": "<Alice|Bob|Carol|Eve|Dave>"}}
"""

AGENT_4_INSTRUCTION = f"""
You are Agent 4. You have the following information:
{INFORMATION_AGENT_4}

Read the discussion so far.
Give a short opinion.

End with this exact metadata format:

METADATA_JSON:
{{"agent": "agent_4", "vote": "<Alice|Bob|Carol|Eve|Dave>"}}
"""