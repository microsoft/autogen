from dataclasses import dataclass
from typing import List, Protocol

from autogen_agentchat.agents._base_chat_agent import ChatMessage


@dataclass
class TeamRunResult:
    messages: List[ChatMessage]


class BaseTeam(Protocol):
    async def run(self, task: str) -> TeamRunResult:
        """Run the team and return the result."""
        ...
