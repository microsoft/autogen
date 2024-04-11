import asyncio
import functools
import json
from typing import Any, Awaitable, Callable, List, Union

from ..agent import Agent, GenerateReplyResult
from ..types import AssistantMessage, FunctionCallMessage, FunctionCallResult, MessageAndSender
from .assistant_agent import FunctionInfo


class FunctionCallingAgent(Agent):
    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        functions: List[Union[Callable[..., Any], FunctionInfo]] = [],
    ):
        self._name = name
        self._description = description

        def _name(func: Union[Callable[..., Any], FunctionInfo]) -> str:
            if isinstance(func, dict):
                return func.get("name", func.get("func").__name__)
            else:
                return func.__name__

        def _func(func: Union[Callable[..., Any], FunctionInfo]) -> Any:
            if isinstance(func, dict):
                return func.get("func")
            else:
                return func

        self._functions = dict([(_name(x), _func(x)) for x in functions])

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
        messages: List[MessageAndSender],
    ) -> GenerateReplyResult:
        last_message = messages[-1]
        if not isinstance(last_message, AssistantMessage):
            return AssistantMessage(content="I can only call functions")

        if last_message.function_calls is None or len(last_message.function_calls) == 0:
            return AssistantMessage(content="No functions to call")

        ids: List[str] = []
        results: List[Awaitable[Any]] = []
        for function_call in last_message.function_calls:
            if function_call.name in self._functions:
                function = self._functions[function_call.name]
                arguments = json.loads(function_call.arguments)
                ids.append(function_call.id)
                if asyncio.iscoroutinefunction(function):
                    results.append(function(**arguments))
                else:
                    results.append(
                        asyncio.get_event_loop().run_in_executor(None, functools.partial(function, **arguments))
                    )

        # TODO handle exceptions
        results = await asyncio.gather(*results)
        return FunctionCallMessage(
            call_results=[FunctionCallResult(content=str(result), call_id=id) for result, id in zip(results, ids)]
        )
