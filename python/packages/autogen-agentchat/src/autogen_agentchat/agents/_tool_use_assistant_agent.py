import logging
import warnings
from typing import Any, Awaitable, Callable, List

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_core.tools import Tool

from .. import EVENT_LOGGER_NAME
from ._assistant_agent import AssistantAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class ToolUseAssistantAgent(AssistantAgent):
    """[DEPRECATED] An agent that provides assistance with tool use.

    It responds with a StopMessage when 'terminate' is detected in the response.

    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client to use for inference.
        registered_tools (List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]): The tools to register with the agent.
        description (str, optional): The description of the agent.
        system_message (str, optional): The system message for the model.
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        registered_tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]],
        *,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: str = "You are a helpful AI assistant. Solve tasks using your tools. Reply with 'TERMINATE' when the task has been completed.",
    ):
        # Deprecation warning.
        warnings.warn(
            "ToolUseAssistantAgent is deprecated. Use AssistantAgent instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            name, model_client, tools=registered_tools, description=description, system_message=system_message
        )
