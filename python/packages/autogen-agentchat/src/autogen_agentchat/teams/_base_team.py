import logging
from dataclasses import dataclass
from typing import List, Protocol

from autogen_agentchat.agents._base_chat_agent import ChatMessage

from ..logging import EVENT_LOGGER_NAME, ConsoleLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.INFO)
console_handler = ConsoleLogHandler()
logger.addHandler(console_handler)


@dataclass
class TeamRunResult:
    messages: List[ChatMessage]


class BaseTeam(Protocol):
    async def run(self, task: str) -> TeamRunResult:
        """Run the team and return the result."""
        ...
