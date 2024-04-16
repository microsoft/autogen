from typing import List

from autogen.experimental.chat_history import ChatHistoryReadOnly

from ..agent import Agent
from ..speaker_selection import SpeakerSelection


class RoundRobin(SpeakerSelection):
    def __init__(self) -> None:
        self._current_speaker_index = 0

    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent:
        self._current_speaker_index = self._current_speaker_index % len(agents)
        speaker = agents[self._current_speaker_index]
        self._current_speaker_index += 1
        return speaker
