import asyncio
import json
from typing import Any, Coroutine, Dict, List, Mapping, Sequence, Tuple

from ...components import (
    FunctionCall,
    TypeRoutedAgent,
    message_handler,
)
from ...components.models import (
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    SystemMessage,
)
from ...components.tools import Tool
from ...core import AgentRuntime, CancellationToken
from ..memory import ChatMemory
from ..types import (
    FunctionCallMessage,
    Message,
    Reset,
    RespondNow,
    ResponseFormat,
    TextMessage,
)
from ..utils import convert_messages_to_llm_messages
from .base import BaseChatAgent


class ChatCompletionAgent(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        system_messages: List[SystemMessage],
        memory: ChatMemory,
        model_client: ChatCompletionClient,
        tools: Sequence[Tool] = [],
    ) -> None:
        super().__init__(name, description, runtime)
        self._system_messages = system_messages
        self._client = model_client
        self._memory = memory
        self._tools = tools

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        # Add a user message.
        self._memory.add_message(message)

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        # Reset the chat messages.
        self._memory.clear()

    @message_handler()
    async def on_respond_now(
        self, message: RespondNow, cancellation_token: CancellationToken
    ) -> TextMessage | FunctionCallMessage:
        # Get a response from the model.
        response = await self._client.create(
            self._system_messages + convert_messages_to_llm_messages(self._memory.get_messages(), self.name),
            tools=self._tools,
            json_output=message.response_format == ResponseFormat.json_object,
        )

        # If the agent has function executor, and the response is a list of
        # tool calls, iterate with itself until we get a response that is not a
        # list of tool calls.
        while (
            len(self._tools) > 0
            and isinstance(response.content, list)
            and all(isinstance(x, FunctionCall) for x in response.content)
        ):
            # Send a function call message to itself.
            response = await self._send_message(
                message=FunctionCallMessage(content=response.content, source=self.name),
                recipient=self,
                cancellation_token=cancellation_token,
            )
            # Make an assistant message from the response.
            response = await self._client.create(
                self._system_messages + convert_messages_to_llm_messages(self._memory.get_messages(), self.name),
                tools=self._tools,
                json_output=message.response_format == ResponseFormat.json_object,
            )

        final_response: Message
        if isinstance(response.content, str):
            # If the response is a string, return a text message.
            final_response = TextMessage(content=response.content, source=self.name)
        elif isinstance(response.content, list) and all(isinstance(x, FunctionCall) for x in response.content):
            # If the response is a list of function calls, return a function call message.
            final_response = FunctionCallMessage(content=response.content, source=self.name)
        else:
            raise ValueError(f"Unexpected response: {response.content}")

        # Add the response to the chat messages.
        self._memory.add_message(final_response)

        # Return the response.
        return final_response

    @message_handler()
    async def on_tool_call_message(
        self, message: FunctionCallMessage, cancellation_token: CancellationToken
    ) -> FunctionExecutionResultMessage:
        if len(self._tools) == 0:
            raise ValueError("No tools available")

        # Add a tool call message.
        self._memory.add_message(message)

        # Execute the tool calls.
        results: List[FunctionExecutionResult] = []
        execution_futures: List[Coroutine[Any, Any, Tuple[str, str]]] = []
        for function_call in message.content:
            # Parse the arguments.
            try:
                arguments = json.loads(function_call.arguments)
            except json.JSONDecodeError:
                results.append(
                    FunctionExecutionResult(
                        content=f"Error: Could not parse arguments for function {function_call.name}.",
                        call_id=function_call.id,
                    )
                )
                continue
            # Execute the function.
            future = self.execute_function(
                function_call.name,
                arguments,
                function_call.id,
                cancellation_token=cancellation_token,
            )
            # Append the async result.
            execution_futures.append(future)
        if execution_futures:
            # Wait for all async results.
            execution_results = await asyncio.gather(*execution_futures)
            # Add the results.
            for execution_result, call_id in execution_results:
                results.append(FunctionExecutionResult(content=execution_result, call_id=call_id))

        # Create a tool call result message.
        tool_call_result_msg = FunctionExecutionResultMessage(content=results)

        # Add tool call result message.
        self._memory.add_message(tool_call_result_msg)

        # Return the results.
        return tool_call_result_msg

    async def execute_function(
        self,
        name: str,
        args: Dict[str, Any],
        call_id: str,
        cancellation_token: CancellationToken,
    ) -> Tuple[str, str]:
        # Find tool
        tool = next((t for t in self._tools if t.name == name), None)
        if tool is None:
            return (f"Error: tool {name} not found.", call_id)
        try:
            result = await tool.run_json(args, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
        except Exception as e:
            result_as_str = f"Error: {str(e)}"
        return (result_as_str, call_id)

    def save_state(self) -> Mapping[str, Any]:
        return {
            "description": self.description,
            "memory": self._memory.save_state(),
            "system_messages": self._system_messages,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._memory.load_state(state["memory"])
        self._system_messages = state["system_messages"]
        self._description = state["description"]
