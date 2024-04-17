from typing import Awaitable, List, Protocol, Union

from .agent import Agent
from .chat_history import ChatHistoryReadOnly


class SpeakerSelection(Protocol):
    def select_speaker(
        self, agents: List[Agent], chat_history: ChatHistoryReadOnly
    ) -> Union[Awaitable[Agent], Agent]: ...
