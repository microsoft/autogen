__all__ = [
    "CantHandleException",
    "UndeliverableException",
    "MessageDroppedException",
    "NotAccessibleError",
    "RecipientNotFoundError",
]


class CantHandleException(Exception):
    """Raised when a handler can't handle the exception."""


class UndeliverableException(Exception):
    """Raised when a message can't be delivered."""


class MessageDroppedException(Exception):
    """Raised when a message is dropped."""


class NotAccessibleError(Exception):
    """Tried to access a value that is not accessible. For example if it is remote cannot be accessed locally."""


class RecipientNotFoundError(Exception):
    """Raised when a message is sent to an agent type that is not registered in the runtime.

    Args:
        recipient: The :class:`~autogen_core.AgentId` that could not be found.

    .. versionadded:: v0.4.10
    """
