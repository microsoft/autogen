from typing import Optional, Union

from ..agent import Agent, AgentStream
from ..chat_summarizers.last_message import LastMessageSummarizer
from ..speaker_selection_strategies.round_robin_speaker_selection import RoundRobin
from ..summarizer import ChatSummarizer
from ..termination import TerminationManager
from ..termination_managers.default_termination_manager import DefaultTerminationManager
from ..types import Message, MessageAndSender
from .group_chat import GroupChat


class TwoAgentChat(GroupChat):
    def __init__(
        self,
        first: Union[Agent, AgentStream],
        second: Union[Agent, AgentStream],
        *,
        termination_manager: TerminationManager = DefaultTerminationManager(),
        summarizer: ChatSummarizer = LastMessageSummarizer(),
        initial_message: Optional[Union[str, MessageAndSender, Message]] = None
    ):
        super().__init__(
            agents=[first, second],
            speaker_selection=RoundRobin(),
            termination_manager=termination_manager,
            summarizer=summarizer,
            initial_message=initial_message,
            send_introduction=False,
        )
