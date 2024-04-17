from typing import Awaitable, List, Protocol, Tuple, Union

from .agent import Agent
from .chat_history import ChatHistoryReadOnly

# Can optionally return a string to indicate the reason for selecting the speaker
SpeakerSelectionResult = Union[Awaitable[Agent], Awaitable[Tuple[Agent, str]], Agent, Tuple[Agent, str]]


class SpeakerSelection(Protocol):
    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> SpeakerSelectionResult: ...
