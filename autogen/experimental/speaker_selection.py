from typing import List, Protocol

from .agent import Agent
from .types import MessageAndSender


class SpeakerSelectionStrategy(Protocol):
    def select_speaker(self, agents: List[Agent], chat_history: List[MessageAndSender]) -> Agent: ...
