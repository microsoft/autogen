import warnings
from typing import Any, AsyncGenerator, Callable, List, Optional, Union

from typing_extensions import NotRequired, Required, TypedDict

from autogen.experimental.utils import convert_messages_to_llm_messages

from ...cache import AbstractCache
from ...function_utils import get_function_schema
from ..agent import AgentStream
from ..chat_history import ChatHistoryReadOnly
from ..model_client import ModelClient
from ..types import (
    FunctionCallMessage,
    FunctionDefinition,
    GenerateReplyResult,
    IntermediateResponse,
    Message,
    PartialContent,
    SystemMessage,
    TextMessage,
)


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
        name = func_info.get("name", func_info["func"].__name__)
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
            # If no description is provided, use the system message as the description
            self._description = system_message
        else:
            # raise a warning if no description is set
            warnings.warn(f"Description of {self.__class__.__name__} is not set.")

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
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:
        # TODO support tools
        all_messages: List[Message] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(chat_history.messages)

        llm_messages = convert_messages_to_llm_messages(all_messages, self.name)
        response = await self._model_client.create(llm_messages, self._cache, functions=self._functions)

        if isinstance(response.content, str):
            return TextMessage(content=response.content, source=self.name)
        else:
            return FunctionCallMessage(response.content, source=self.name)

    async def stream_generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> AsyncGenerator[Union[IntermediateResponse, GenerateReplyResult], None]:
        all_messages: List[Message] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(chat_history.messages)

        final_message = None
        llm_messages = convert_messages_to_llm_messages(all_messages, self.name)
        async for response in self._model_client.create_stream(llm_messages, self._cache, functions=self._functions):
            if isinstance(response, str):
                yield IntermediateResponse(item=PartialContent(response))

            else:
                if isinstance(response.content, str):
                    final_message = TextMessage(content=response.content, source=self.name)
                    break
                else:
                    final_message = FunctionCallMessage(response.content, source=self.name)
                    break

        assert final_message is not None
        yield final_message
