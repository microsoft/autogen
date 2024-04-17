from typing import List, Tuple

from ..agent import Agent
from ..chat_history import ChatHistoryReadOnly
from ..speaker_selection import SpeakerSelection


class RoundRobin(SpeakerSelection):
    def __init__(self) -> None:
        self._current_speaker_index = 0

    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Tuple[Agent, None]:
        self._current_speaker_index = self._current_speaker_index % len(agents)
        speaker = agents[self._current_speaker_index]
        self._current_speaker_index += 1
        return speaker, None
