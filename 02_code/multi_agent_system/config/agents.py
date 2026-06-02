"""Participant identities for the hiring-panel simulation."""

AGENT_PERSONAS = {
    "sarah_mitchell": {
        "name": "Sarah Mitchell",
        "role": "HR Selection Specialist for Flight Operations",
    },
    "james_carter": {
        "name": "James Carter",
        "role": "Pilot Assessment Specialist",
    },
    "emily_brooks": {
        "name": "Emily Brooks",
        "role": "Recruiting Specialist for Cockpit Personnel",
    },
}

AGENT_ORDER = tuple(AGENT_PERSONAS)


def agent_persona(agent_key: str | None) -> dict:
    """Return the configured persona for an agent key."""
    if not agent_key:
        agent_key = "unknown_agent"
    return AGENT_PERSONAS.get(
        agent_key,
        {
            "name": agent_key.replace("_", " ").title(),
            "role": "HR Selection Panel Member",
        },
    )


def agent_name_for_key(agent_key: str | None) -> str:
    """Return the human-readable name for an agent key."""
    return agent_persona(agent_key)["name"]


def agent_display_name(agent_key: str | None) -> str:
    """Return the human-readable name and role for an agent key."""
    persona = agent_persona(agent_key)
    return f"{persona['name']}, {persona['role']}"
