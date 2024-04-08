from typing import List, Optional


from ..model_client import ModelClient
from ..types import AssistantMessage, ChatMessage, SystemMessage

from ...cache import AbstractCache
from ..agent import Agent


class AssistantAgent(Agent):

    def __init__(
        self,
        *,
        name: str,
        model_client: ModelClient,
        description: Optional[str] = None,
        system_message: Optional[str] = "You are a helpful AI Assistant.",
        cache: Optional[AbstractCache] = None,
    ):
        self._name = name
        self._system_message = SystemMessage(content=system_message) if system_message is not None else None

        if description is not None:
            self._description = description
        elif system_message is not None:
            self._description = system_message
        else:
            """"""

        self._cache = cache
        self._model_client = model_client

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    async def generate_reply(
        self,
        messages: List[ChatMessage],
    ) -> ChatMessage:
        # TODO support tools
        all_messages: List[ChatMessage] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(messages)
        response = await self._model_client.create(all_messages, self._cache)
        if isinstance(response.content, str):
            return AssistantMessage(content=response.content)
        else:
            raise NotImplementedError("Tools not supported yet.")

    def reset(self) -> None:
        """Reset the agent's state."""
        pass
