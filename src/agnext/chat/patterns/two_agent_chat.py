from agnext.chat.patterns.group_chat import GroupChat, GroupChatOutput

from ...core import AgentRuntime
from ..agents.base import BaseChatAgent


# TODO: rewrite this with a new message type calling for add to message
# history.
class TwoAgentChat(GroupChat):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        initial_sender: BaseChatAgent,
        initial_recipient: BaseChatAgent,
        num_rounds: int,
        output: GroupChatOutput,
    ) -> None:
        super().__init__(
            name,
            description,
            runtime,
            [initial_recipient, initial_sender],
            num_rounds,
            output,
        )
