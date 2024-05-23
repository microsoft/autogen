from ..application_components.single_threaded_agent_runtime import (
    SingleThreadedAgentRuntime,
)
from .messages import ChatMessage


# The built-in runtime for the chat API.
class SingleThreadedRuntime(SingleThreadedAgentRuntime[ChatMessage]):
    pass


# Each new built-in runtime should be able to handle ChatMessage type.
