from typing import List, Protocol, Union, runtime_checkable

from .types import ChatMessage


@runtime_checkable
class Agent(Protocol):
    """(In preview) A protocol for Agent.

    An agent can communicate with other agents and perform actions.
    Different agents can differ in what actions they perform in the `receive` method.
    """

    @property
    def name(self) -> str:
        """The name of the agent."""
        ...

    @property
    def description(self) -> str:
        """The description of the agent. Used for the agent's introduction in
        a group chat setting."""
        ...

    def reset(self) -> None:
        """Reset the agent's state."""
        ...

    async def generate_reply(
        self,
        messages: List[ChatMessage],
    ) -> ChatMessage: ...
