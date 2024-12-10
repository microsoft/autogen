from typing import TypeVar

from pydantic import BaseModel
from typing_extensions import deprecated

from ...tools import (
    BaseTool as BaseToolAlias,
)
from ...tools import (
    BaseToolWithState as BaseToolWithStateAlias,
)
from ...tools import (
    CodeExecutionInput as CodeExecutionInputAlias,
)
from ...tools import (
    CodeExecutionResult as CodeExecutionResultAlias,
)
from ...tools import FunctionTool as FunctionToolAlias
from ...tools import (
    ParametersSchema as ParametersSchemaAlias,
)
from ...tools import (
    PythonCodeExecutionTool as PythonCodeExecutionToolAlias,
)
from ...tools import (
    Tool as ToolAlias,
)
from ...tools import (
    ToolSchema as ToolSchemaAlias,
)

__all__ = [
    "Tool",
    "ToolSchema",
    "ParametersSchema",
    "BaseTool",
    "BaseToolWithState",
    "PythonCodeExecutionTool",
    "CodeExecutionInput",
    "CodeExecutionResult",
    "FunctionTool",
]


ArgsT = TypeVar("ArgsT", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", bound=BaseModel, covariant=True)
StateT = TypeVar("StateT", bound=BaseModel)


@deprecated(
    "autogen_core.tools.BaseToolAlias moved to autogen_core.tools.BaseToolAlias. This alias will be removed in 0.4.0."
)
class BaseTool(BaseToolAlias[ArgsT, ReturnT]):
    pass


@deprecated("autogen_core.tools.ToolAlias moved to autogen_core.tools.ToolAlias. This alias will be removed in 0.4.0.")
class Tool(ToolAlias):
    pass


@deprecated(
    "autogen_core.tools.ToolSchemaAlias moved to autogen_core.tools.ToolSchemaAlias. This alias will be removed in 0.4.0."
)
class ToolSchema(ToolSchemaAlias):
    pass


@deprecated(
    "autogen_core.tools.ParametersSchemaAlias moved to autogen_core.tools.ParametersSchemaAlias. This alias will be removed in 0.4.0."
)
class ParametersSchema(ParametersSchemaAlias):
    pass


@deprecated(
    "autogen_core.tools.BaseToolWithStateAlias moved to autogen_core.tools.BaseToolWithStateAlias. This alias will be removed in 0.4.0."
)
class BaseToolWithState(BaseToolWithStateAlias[ArgsT, ReturnT, StateT]):
    pass


@deprecated(
    "autogen_core.tools.PythonCodeExecutionToolAlias moved to autogen_core.tools.PythonCodeExecutionToolAlias. This alias will be removed in 0.4.0."
)
class PythonCodeExecutionTool(PythonCodeExecutionToolAlias):
    pass


@deprecated(
    "autogen_core.tools.CodeExecutionInputAlias moved to autogen_core.tools.CodeExecutionInputAlias. This alias will be removed in 0.4.0."
)
class CodeExecutionInput(CodeExecutionInputAlias):
    pass


@deprecated(
    "autogen_core.tools.CodeExecutionResultAlias moved to autogen_core.tools.CodeExecutionResultAlias. This alias will be removed in 0.4.0."
)
class CodeExecutionResult(CodeExecutionResultAlias):
    pass


@deprecated(
    "autogen_core.tools.FunctionToolAlias moved to autogen_core.tools.FunctionToolAlias. This alias will be removed in 0.4.0."
)
class FunctionTool(FunctionToolAlias):
    pass
