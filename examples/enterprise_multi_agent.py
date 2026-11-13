"""
Enterprise Multi-Agent Pattern with AutoGen
Author: Rehan Malik

Production pattern for multi-agent code review and analysis.
Uses structured outputs and conversation management.
"""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class AgentConfig:
    """Configuration for an enterprise agent."""
    name: str
    role: str
    system_message: str
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 2000
    tools: list = field(default_factory=list)


@dataclass
class ConversationTurn:
    agent: str
    message: str
    tool_calls: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class EnterpriseConversation:
    """Managed multi-agent conversation with guardrails."""

    def __init__(self, max_turns: int = 10, require_structured_output: bool = True):
        self.agents: dict[str, AgentConfig] = {}
        self.history: list[ConversationTurn] = []
        self.max_turns = max_turns
        self.require_structured_output = require_structured_output

    def register_agent(self, config: AgentConfig):
        self.agents[config.name] = config

    def add_turn(self, agent_name: str, message: str, **kwargs):
        turn = ConversationTurn(agent=agent_name, message=message, **kwargs)
        self.history.append(turn)
        return turn

    def get_context(self, agent_name: str, max_context_turns: int = 5) -> str:
        """Get conversation context for an agent."""
        recent = self.history[-max_context_turns:]
        lines = []
        for turn in recent:
            lines.append(f"[{turn.agent}]: {turn.message}")
        return "\n".join(lines)

    def should_continue(self) -> bool:
        return len(self.history) < self.max_turns

    def summary(self) -> dict:
        agents_involved = set(t.agent for t in self.history)
        return {
            "total_turns": len(self.history),
            "agents_involved": list(agents_involved),
            "tool_calls": sum(len(t.tool_calls) for t in self.history),
        }


def create_code_review_team() -> EnterpriseConversation:
    """Create a production code review multi-agent team."""
    conv = EnterpriseConversation(max_turns=15)

    conv.register_agent(AgentConfig(
        name="architect",
        role="Senior Architect",
        system_message=(
            "You are a senior software architect. Review code for architecture patterns, "
            "SOLID principles, and scalability concerns. Be constructive."
        ),
    ))

    conv.register_agent(AgentConfig(
        name="security_reviewer",
        role="Security Engineer",
        system_message=(
            "You are a security engineer. Review code for vulnerabilities, "
            "input validation, authentication issues, and data exposure risks."
        ),
    ))

    conv.register_agent(AgentConfig(
        name="performance_reviewer",
        role="Performance Engineer",
        system_message=(
            "You are a performance engineer. Review code for efficiency, "
            "memory usage, algorithmic complexity, and caching opportunities."
        ),
    ))

    return conv


if __name__ == "__main__":
    team = create_code_review_team()

    team.add_turn("user", "Please review this authentication module for our API gateway.")
    team.add_turn("architect", "The module follows a clean middleware pattern. Consider extracting the token validation into a separate service for reuse.")
    team.add_turn("security_reviewer", "Found 2 issues: 1) Token expiry not checked, 2) Missing rate limiting on auth endpoints.")
    team.add_turn("performance_reviewer", "Token validation should be cached (Redis recommended) to avoid repeated crypto operations.")

    print(json.dumps(team.summary(), indent=2))
