from typing import Awaitable, List, Optional, Protocol, Tuple, Union

from .agent import Agent
from .chat_history import ChatHistoryReadOnly

# Can optionally return a string to indicate the reason for selecting the speaker
SpeakerSelectionResult = Union[Awaitable[Tuple[Agent, Optional[str]]], Tuple[Agent, Optional[str]]]


class SpeakerSelection(Protocol):
    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> SpeakerSelectionResult: ...
