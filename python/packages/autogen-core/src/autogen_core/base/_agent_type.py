from dataclasses import dataclass


@dataclass(eq=True, frozen=True)
class AgentType:
    type: str
    """String representation of this agent type."""
