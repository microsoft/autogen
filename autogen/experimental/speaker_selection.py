from typing import List, Optional, Protocol

from .agent import Agent
from .types import ChatMessage


class SpeakerSelectionStrategy(Protocol):

    # Is None on the first turn
    def select_speaker(
        self, current_speaker: Optional[Agent], agents: List[Agent], chat_history: List[ChatMessage]
    ) -> Agent: ...
