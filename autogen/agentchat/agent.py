from typing import Any, Callable, Dict, List, Optional, Protocol, Union, runtime_checkable


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

    def send(
        self,
        message: Union[Dict[str, Any], str],
        recipient: "Agent",
        request_reply: Optional[bool] = None,
    ) -> None:
        """Send a message to another agent."""
        ...

    async def a_send(
        self,
        message: Union[Dict[str, Any], str],
        recipient: "Agent",
        request_reply: Optional[bool] = None,
    ) -> None:
        """(Async) Send a message to another agent."""
        ...

    def receive(
        self, message: Union[Dict[str, Any], str], sender: "Agent", request_reply: Optional[bool] = None
    ) -> None:
        """Receive a message from another agent."""

    async def a_receive(
        self, message: Union[Dict[str, Any], str], sender: "Agent", request_reply: Optional[bool] = None
    ) -> None:
        """(Async) Receive a message from another agent."""
        ...

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict[str, Any], None]:
        """Generate a reply based on the received messages.

        Args:
            messages (list[dict]): a list of messages received.
            sender: sender of an Agent instance.
        Returns:
            str or dict or None: the generated reply. If None, no reply is generated.
        """

    async def a_generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict[str, Any], None]:
        """(Async) Generate a reply based on the received messages.

        Args:
            messages (list[dict]): a list of messages received.
            sender: sender of an Agent instance.
        Returns:
            str or dict or None: the generated reply. If None, no reply is generated.
        """


@runtime_checkable
class LLMAgent(Agent, Protocol):
    """(In preview) A protocol for an LLM agent."""

    @property
    def system_message(self) -> str:
        """The system message of this agent."""

    def update_system_message(self, system_message: str) -> None:
        """Update this agent's system message.

        Args:
            system_message (str): system message for inference.
        """
