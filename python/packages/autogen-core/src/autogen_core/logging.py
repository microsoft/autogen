import json
from enum import Enum
from typing import Any, Dict, cast

from ._agent_id import AgentId
from ._topic import TopicId


class LLMCallEvent:
    def __init__(
        self,
        *,
        messages: Dict[str, Any],
        response: Dict[str, Any],
        prompt_tokens: int,
        completion_tokens: int,
        agent_id: AgentId | None = None,
        **kwargs: Any,
    ) -> None:
        """To be used by model clients to log the call to the LLM.

        Args:
            messages (Dict[str, Any]): The messages of the call. Must be json serializable.
            response (Dict[str, Any]): The response of the call. Must be json serializable.
            prompt_tokens (int): Number of tokens used in the prompt.
            completion_tokens (int): Number of tokens used in the completion.
            agent_id (AgentId | None, optional): The agent id of the model. Defaults to None.

        Example:

            .. code-block:: python

                from autogen_core import EVENT_LOGGER_NAME
                from autogen_core.logging import LLMCallEvent

                logger = logging.getLogger(EVENT_LOGGER_NAME)
                logger.info(LLMCallEvent(prompt_tokens=10, completion_tokens=20))

        """
        self.kwargs = kwargs
        self.kwargs["type"] = "LLMCall"
        self.kwargs["messages"] = messages
        self.kwargs["response"] = response
        self.kwargs["prompt_tokens"] = prompt_tokens
        self.kwargs["completion_tokens"] = completion_tokens
        self.kwargs["agent_id"] = None if agent_id is None else str(agent_id)
        self.kwargs["type"] = "LLMCall"

    @property
    def prompt_tokens(self) -> int:
        return cast(int, self.kwargs["prompt_tokens"])

    @property
    def completion_tokens(self) -> int:
        return cast(int, self.kwargs["completion_tokens"])

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)


class MessageKind(Enum):
    DIRECT = 1
    PUBLISH = 2
    RESPOND = 3


class DeliveryStage(Enum):
    SEND = 1
    DELIVER = 2


class MessageEvent:
    def __init__(
        self,
        *,
        payload: str,
        sender: AgentId | None,
        receiver: AgentId | TopicId | None,
        kind: MessageKind,
        delivery_stage: DeliveryStage,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs
        self.kwargs["payload"] = payload
        self.kwargs["sender"] = None if sender is None else str(sender)
        self.kwargs["receiver"] = None if receiver is None else str(receiver)
        self.kwargs["kind"] = str(kind)
        self.kwargs["delivery_stage"] = str(delivery_stage)
        self.kwargs["type"] = "Message"

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)


class MessageDroppedEvent:
    def __init__(
        self,
        *,
        payload: str,
        sender: AgentId | None,
        receiver: AgentId | TopicId | None,
        kind: MessageKind,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs
        self.kwargs["payload"] = payload
        self.kwargs["sender"] = None if sender is None else str(sender)
        self.kwargs["receiver"] = None if receiver is None else str(receiver)
        self.kwargs["kind"] = str(kind)
        self.kwargs["type"] = "MessageDropped"

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)


class MessageHandlerExceptionEvent:
    def __init__(
        self,
        *,
        payload: str,
        handling_agent: AgentId,
        exception: BaseException,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs
        self.kwargs["payload"] = payload
        self.kwargs["handling_agent"] = str(handling_agent)
        self.kwargs["exception"] = str(exception)
        self.kwargs["type"] = "MessageHandlerException"

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)


class AgentConstructionExceptionEvent:
    def __init__(
        self,
        *,
        agent_id: AgentId,
        exception: BaseException,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs
        self.kwargs["agent_id"] = str(agent_id)
        self.kwargs["exception"] = str(exception)
        self.kwargs["type"] = "AgentConstructionException"

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)
