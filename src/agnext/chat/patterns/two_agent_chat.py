from agnext.chat.patterns.group_chat import GroupChat, GroupChatOutput

from ...core import AgentRuntime
from ..agents.base import BaseChatAgent


class TwoAgentChat(GroupChat):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        agent1: BaseChatAgent,
        agent2: BaseChatAgent,
        num_rounds: int,
        output: GroupChatOutput,
    ) -> None:
        super().__init__(name, description, runtime, [agent1, agent2], num_rounds, output)
