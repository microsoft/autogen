class CantHandleException(Exception):
    """Raised when a handler can't handle the exception."""


class UndeliverableException(Exception):
    """Raised when a message can't be delivered."""
