import json
import re
from pathlib import Path
from typing import Iterable

from .metrics import metrics

TASK_PATH = Path(__file__).parent / "hidden_profile_task.json"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MEMORY_BLOCK_START = "MEMORY_UPDATE_START"
MEMORY_BLOCK_END = "MEMORY_UPDATE_END"


def load_task() -> dict:
    with TASK_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


TASK = load_task()
AGENT_KEYS = ["agent_1", "agent_2", "agent_3", "agent_4"]


def _as_bullets(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def _agent_memory_path(agent_key: str) -> Path:
    return PROJECT_ROOT / "subagents" / agent_key / f"{agent_key}.md"


def _round_number() -> int:
    return metrics.loop_count + 1


def build_memory_template(agent_key: str, round_number: int | None = None) -> str:
    round_number = round_number or _round_number()
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")

    candidate_rows = "\n".join(
        f"| {candidate} |  |  |  |  |" for candidate in candidates
    )

    return (
        f"# Shared Mental Model (Agent {agent_key.split('_')[-1]}, Round {round_number})\n\n"
        "## Task Summary\n"
        f"Goal\n{goal}\n\n"
        f"Candidates\n{_as_bullets(candidates)}\n\n"
        f"Public Information\n{_as_bullets(public_info)}\n\n"
        f"Private Information\n{_as_bullets(private_info)}\n\n"
        "## Candidate Summary Table\n"
        "| Candidate | Evidence For | Evidence Against | Fit for Role | Notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{candidate_rows}\n\n"
        "## Current Preference\n"
        "Leading Candidate\n- \n\n"
        "Rationale\n- \n\n"
        "Confidence (percent)\n- \n\n"
        "Uncertainties\n- \n\n"
        "## Open Questions\n"
        "Missing evidence\n- \n\n"
        "What would change the decision\n- \n\n"
        "## Next-Step Focus\n"
        "What to ask or look for in the next round\n- \n"
    )


def read_agent_memory(agent_key: str, round_number: int | None = None) -> str:
    path = _agent_memory_path(agent_key)
    if not path.exists():
        return build_memory_template(agent_key, round_number)

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return build_memory_template(agent_key, round_number)

    return content


def write_agent_memory(agent_key: str, content: str) -> None:
    path = _agent_memory_path(agent_key)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def reset_all_agent_memories(round_number: int | None = 1) -> None:
    for agent_key in AGENT_KEYS:
        template = build_memory_template(agent_key, round_number)
        write_agent_memory(agent_key, template)


def extract_memory_block(text: str) -> str | None:
    match = re.search(
        rf"{MEMORY_BLOCK_START}\s*(.*?)\s*{MEMORY_BLOCK_END}",
        text,
        re.DOTALL,
    )
    if not match:
        return None

    return match.group(1).strip()


def build_agent_instruction(agent_key: str) -> str:
    round_number = _round_number()
    memory = read_agent_memory(agent_key, round_number)
    public_info = TASK.get("public_information", [])
    private_info = TASK.get("private_information", {}).get(agent_key, [])
    candidates = TASK.get("candidates", [])
    goal = TASK.get("goal", "")
    other_agents = [key for key in AGENT_KEYS if key != agent_key]

    return (
        f"You are {agent_key.replace('_', ' ').title()}.\n\n"
        "Task context (use in your reasoning and memory update):\n"
        f"Goal: {goal}\n"
        f"Candidates: {', '.join(candidates)}\n"
        f"Public information:\n{_as_bullets(public_info)}\n"
        f"Private information:\n{_as_bullets(private_info)}\n\n"
        f"You may call other agents as tools: {', '.join(other_agents)}.\n"
        "If you have a specific question, ask it via the relevant agent tool.\n"
        "If another agent asks you a question, answer with what you know.\n"
        "Use tool calls sparingly and only to clarify missing facts.\n\n"
        "Current memory (update and return a full replacement):\n"
        f"{memory}\n\n"
        "Read the discussion so far and give a short opinion.\n"
        "Then output a full updated memory block using this exact format:\n\n"
        f"{MEMORY_BLOCK_START}\n"
        "<complete Shared Mental Model markdown>\n"
        f"{MEMORY_BLOCK_END}\n\n"
        "End with this exact metadata format:\n\n"
        "METADATA_JSON:\n"
        f"{{\"agent\": \"{agent_key}\", \"vote\": \"<Alice|Bob|Carol|Eve|Dave>\"}}\n"
    )