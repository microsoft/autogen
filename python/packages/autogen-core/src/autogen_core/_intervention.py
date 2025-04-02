from typing import Any, Protocol, final

from ._agent_id import AgentId
from ._message_context import MessageContext

__all__ = [
    "DropMessage",
    "InterventionHandler",
    "DefaultInterventionHandler",
]


@final
class DropMessage:
    """Marker type for signalling that a message should be dropped by an intervention handler. The type itself should be returned from the handler."""

    ...


class InterventionHandler(Protocol):
    """An intervention handler is a class that can be used to modify, log or drop messages that are being processed by the :class:`autogen_core.base.AgentRuntime`.

    The handler is called when the message is submitted to the runtime.

    Currently the only runtime which supports this is the :class:`autogen_core.base.SingleThreadedAgentRuntime`.

    Note: Returning None from any of the intervention handler methods will result in a warning being issued and treated as "no change". If you intend to drop a message, you should return :class:`DropMessage` explicitly.

    Example:

    .. code-block:: python

        from autogen_core import DefaultInterventionHandler, MessageContext, AgentId, SingleThreadedAgentRuntime
        from dataclasses import dataclass
        from typing import Any


        @dataclass
        class MyMessage:
            content: str


        class MyInterventionHandler(DefaultInterventionHandler):
            async def on_send(self, message: Any, *, message_context: MessageContext, recipient: AgentId) -> MyMessage:
                if isinstance(message, MyMessage):
                    message.content = message.content.upper()
                return message


        runtime = SingleThreadedAgentRuntime(intervention_handlers=[MyInterventionHandler()])

    """

    async def on_send(
        self, message: Any, *, message_context: MessageContext, recipient: AgentId
    ) -> Any | type[DropMessage]:
        """Called when a message is submitted to the AgentRuntime using :meth:`autogen_core.base.AgentRuntime.send_message`."""
        ...

    async def on_publish(self, message: Any, *, message_context: MessageContext) -> Any | type[DropMessage]:
        """Called when a message is published to the AgentRuntime using :meth:`autogen_core.base.AgentRuntime.publish_message`."""
        ...

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        """Called when a response is received by the AgentRuntime from an Agent's message handler returning a value."""
        ...


class DefaultInterventionHandler(InterventionHandler):
    """Simple class that provides a default implementation for all intervention
    handler methods, that simply returns the message unchanged. Allows for easy
    subclassing to override only the desired methods."""

    async def on_send(
        self, message: Any, *, message_context: MessageContext, recipient: AgentId
    ) -> Any | type[DropMessage]:
        return message

    async def on_publish(self, message: Any, *, message_context: MessageContext) -> Any | type[DropMessage]:
        return message

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        return message
