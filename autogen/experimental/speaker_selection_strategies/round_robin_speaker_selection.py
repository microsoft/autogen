from typing import List, Optional

from ..agent import Agent
from ..types import ChatMessage
from ..speaker_selection import SpeakerSelectionStrategy

class RoundRobin(SpeakerSelectionStrategy):
    def __init__(self) -> None:
        self._current_speaker_index = 0

    def select_speaker(self, current_speaker: Optional[Agent], agents: List[Agent], chat_history: List[ChatMessage]) -> Agent:
        self._current_speaker_index = self._current_speaker_index % len(agents)
        speaker = agents[self._current_speaker_index]
        self._current_speaker_index += 1
        return speaker