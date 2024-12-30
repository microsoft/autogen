from typing_extensions import deprecated

from .._intervention import DefaultInterventionHandler as DefaultInterventionHandlerAlias
from .._intervention import DropMessage as DropMessageAlias
from .._intervention import InterventionHandler as InterventionHandlerAliass

__all__ = [
    "DropMessage",
    "InterventionHandler",
    "DefaultInterventionHandler",
]

# Final so can't inherit and deprecate
DropMessage = DropMessageAlias


@deprecated("Moved to autogen_core.InterventionHandler. Will remove this in 0.4.0.", stacklevel=2)
class InterventionHandler(InterventionHandlerAliass): ...


@deprecated("Moved to autogen_core.DefaultInterventionHandler. Will remove this in 0.4.0.", stacklevel=2)
class DefaultInterventionHandler(DefaultInterventionHandlerAlias): ...
