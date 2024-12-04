from typing_extensions import deprecated

from ..exceptions import (
    CantHandleException as CantHandleExceptionAlias,
)
from ..exceptions import (
    MessageDroppedException as MessageDroppedExceptionAlias,
)
from ..exceptions import (
    NotAccessibleError as NotAccessibleErrorAlias,
)
from ..exceptions import (
    UndeliverableException as UndeliverableExceptionAlias,
)


@deprecated("Moved to autogen_core.exceptions.CantHandleException. Alias will be removed in 0.4.0")
class CantHandleException(CantHandleExceptionAlias):
    """Raised when a handler can't handle the exception."""


@deprecated("Moved to autogen_core.exceptions.UndeliverableException. Alias will be removed in 0.4.0")
class UndeliverableException(UndeliverableExceptionAlias):
    """Raised when a message can't be delivered."""


@deprecated("Moved to autogen_core.exceptions.MessageDroppedException. Alias will be removed in 0.4.0")
class MessageDroppedException(MessageDroppedExceptionAlias):
    """Raised when a message is dropped."""


@deprecated("Moved to autogen_core.exceptions.NotAccessibleError. Alias will be removed in 0.4.0")
class NotAccessibleError(NotAccessibleErrorAlias):
    """Tried to access a value that is not accessible. For example if it is remote cannot be accessed locally."""


__all__ = []  # type: ignore
