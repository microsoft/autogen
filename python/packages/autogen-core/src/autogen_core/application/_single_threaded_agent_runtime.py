from typing_extensions import deprecated

from .._single_threaded_agent_runtime import SingleThreadedAgentRuntime as SingleThreadedAgentRuntimeAlias


@deprecated(
    "autogen_core.application.SingleThreadedAgentRuntime moved to autogen_core.SingleThreadedAgentRuntime. This alias will be removed in 0.4.0."
)
class SingleThreadedAgentRuntime(SingleThreadedAgentRuntimeAlias):
    pass
