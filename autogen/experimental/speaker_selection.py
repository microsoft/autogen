from typing import List, Protocol

from autogen.experimental.chat_history import ChatHistoryReadOnly

from .agent import Agent


class SpeakerSelectionStrategy(Protocol):
    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent: ...
