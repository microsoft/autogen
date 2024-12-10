from typing import Any

from typing_extensions import deprecated

from ...tool_agent import (
    InvalidToolArgumentsException as InvalidToolArgumentsExceptionAlias,
)
from ...tool_agent import (
    ToolAgent as ToolAgentAlias,
)
from ...tool_agent import (
    ToolException as ToolExceptionAlias,
)
from ...tool_agent import (
    ToolExecutionException as ToolExecutionExceptionAlias,
)
from ...tool_agent import (
    ToolNotFoundException as ToolNotFoundExceptionAlias,
)
from ...tool_agent import tool_agent_caller_loop as tool_agent_caller_loop_alias

__all__ = [
    "ToolAgent",
    "ToolException",
    "ToolNotFoundException",
    "InvalidToolArgumentsException",
    "ToolExecutionException",
    "tool_agent_caller_loop",
]


@deprecated(
    "autogen_core.tool_agent.ToolAgentAlias moved to autogen_core.tool_agent.ToolAgentAlias. This alias will be removed in 0.4.0."
)
class ToolAgent(ToolAgentAlias):
    pass


@deprecated(
    "autogen_core.tool_agent.ToolExceptionAlias moved to autogen_core.tool_agent.ToolExceptionAlias. This alias will be removed in 0.4.0."
)
class ToolException(ToolExceptionAlias):
    pass


@deprecated(
    "autogen_core.tool_agent.ToolNotFoundExceptionAlias moved to autogen_core.tool_agent.ToolNotFoundExceptionAlias. This alias will be removed in 0.4.0."
)
class ToolNotFoundException(ToolNotFoundExceptionAlias):
    pass


@deprecated(
    "autogen_core.tool_agent.InvalidToolArgumentsExceptionAlias moved to autogen_core.tool_agent.InvalidToolArgumentsExceptionAlias. This alias will be removed in 0.4.0."
)
class InvalidToolArgumentsException(InvalidToolArgumentsExceptionAlias):
    pass


@deprecated(
    "autogen_core.tool_agent.ToolExecutionExceptionAlias moved to autogen_core.tool_agent.ToolExecutionExceptionAlias. This alias will be removed in 0.4.0."
)
class ToolExecutionException(ToolExecutionExceptionAlias):
    pass


@deprecated(
    "autogen_core.tool_agent.tool_agent_caller_loop moved to autogen_core.tool_agent.tool_agent_caller_loop. This alias will be removed in 0.4.0."
)
def tool_agent_caller_loop(*args: Any, **kwargs: Any) -> Any:
    return tool_agent_caller_loop_alias(*args, **kwargs)  # type: ignore
