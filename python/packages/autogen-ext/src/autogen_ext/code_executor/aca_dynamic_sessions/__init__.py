import warnings
from typing import Any

from ...code_executors import ACADynamicSessionsCodeExecutor


class AzureContainerCodeExecutor(ACADynamicSessionsCodeExecutor):
    """AzureContainerCodeExecutor has been renamed and moved to autogen_ext.code_executors.ACADynamicSessionsCodeExecutor"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "AzureContainerCodeExecutor has been renamed and moved to autogen_ext.code_executors.ACADynamicSessionsCodeExecutor",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


__all__ = [
    "AzureContainerCodeExecutor",
]
