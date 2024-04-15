import logging
from typing import Awaitable, Callable, List, Optional

from ..agent import Agent
from ..types import MessageAndSender, UserMessage, GenerateReplyResult

HumanInputCallback = Callable[[str], Awaitable[str]]

# async def async_human_input(prompt: str) -> str:
#     return await ainput(prompt)

logger = logging.getLogger(__name__)


class UserInputAgent(Agent):
    def __init__(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        human_input_callback: HumanInputCallback,
    ):
        self._name = name

        if description is not None:
            self._description = description
        else:
            """"""

        self._human_input_callback = human_input_callback

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    async def get_human_reply(
        self,
        messages: List[MessageAndSender],
    ) -> Optional[UserMessage]:

        assert self._human_input_callback is not None, "Human input callback is not provided."

        reply = await self._human_input_callback(
            "Provide feedback. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
        )

        if reply == "":
            return None

        if reply.lower() == "exit":
            return UserMessage(content=reply, is_termination=True)

        return UserMessage(content=reply)

    async def generate_reply(
        self,
        messages: List[MessageAndSender],
    ) -> GenerateReplyResult:

        response = None
        while response is None:
            response = await self.get_human_reply(messages)

        return response
