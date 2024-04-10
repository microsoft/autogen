from typing import Any, AsyncGenerator, Callable, List, Optional, Union
from typing_extensions import TypedDict, Required, NotRequired

from ...cache import AbstractCache
from ..agent import AgentStream
from ..model_client import ModelClient
from ..types import AssistantMessage, ChatMessage, FunctionDefinition, PartialContent, StreamResponse, SystemMessage
from ...function_utils import get_function_schema


class FunctionInfo(TypedDict):
    func: Required[Callable[..., Any]]
    name: NotRequired[str]
    description: NotRequired[str]


def _into_function_definition(
    func_info: Union[FunctionInfo, FunctionDefinition, Callable[..., Any]]
) -> FunctionDefinition:
    if isinstance(func_info, FunctionDefinition):
        return func_info
    elif isinstance(func_info, dict):
        name = func_info.get("name", func_info.get("func").__name__)
        description = func_info.get("description", "")
        parameters = get_function_schema(func_info["func"], description="", name="")["function"]["parameters"]
        return FunctionDefinition(name=name, description=description, parameters=parameters)
    else:
        parameters = get_function_schema(func_info, description="", name="")["function"]["parameters"]
        return FunctionDefinition(name=func_info.__name__, description="", parameters=parameters)


class AssistantAgent(AgentStream):
    def __init__(
        self,
        *,
        name: str,
        model_client: ModelClient,
        description: Optional[str] = None,
        system_message: Optional[str] = "You are a helpful AI Assistant.",
        cache: Optional[AbstractCache] = None,
        functions: List[Union[Callable[..., Any], FunctionInfo, FunctionDefinition]] = [],
    ):
        self._name = name
        self._system_message = SystemMessage(content=system_message) if system_message is not None else None

        if description is not None:
            self._description = description
        elif system_message is not None:
            self._description = system_message
        else:
            """"""
        self._functions = [_into_function_definition(func) for func in functions]
        self._cache = cache
        self._model_client = model_client

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    async def generate_reply(
        self,
        messages: List[ChatMessage],
    ) -> ChatMessage:
        # TODO support tools
        all_messages: List[ChatMessage] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(messages)
        response = await self._model_client.create(all_messages, self._cache, functions=self._functions)
        if isinstance(response.content, str):
            return AssistantMessage(content=response.content)
        else:
            return AssistantMessage(function_calls=response.content)

    async def stream_generate_reply(
        self,
        messages: List[ChatMessage],
    ) -> AsyncGenerator[StreamResponse, None]:
        all_messages: List[ChatMessage] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(messages)

        final_message = None
        async for response in self._model_client.create_stream(all_messages, self._cache, functions=self._functions):
            if isinstance(response, str):
                yield PartialContent(response)
            else:
                if isinstance(response.content, str):
                    final_message = AssistantMessage(content=response.content)
                    break
                else:
                    final_message = AssistantMessage(function_calls=response.content)
                    break

        assert final_message is not None
        yield final_message

    def reset(self) -> None:
        """Reset the agent's state."""
        pass
