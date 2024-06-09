from ...core import Agent, AgentRuntime
from .group_chat import GroupChat, GroupChatOutput


# TODO: rewrite this with a new message type calling for add to message
# history.
class TwoAgentChat(GroupChat):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        first_speaker: Agent,
        second_speaker: Agent,
        num_rounds: int,
        output: GroupChatOutput,
    ) -> None:
        super().__init__(
            name,
            description,
            runtime,
            [first_speaker, second_speaker],
            num_rounds,
            output,
        )
