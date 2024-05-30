import asyncio
import json
from typing import Any, Coroutine, Dict, List, Mapping, Tuple

from agnext.agent_components.function_executor import FunctionExecutor
from agnext.agent_components.model_client import ModelClient
from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.agent_components.types import (
    FunctionCall,
    FunctionSignature,
    SystemMessage,
)
from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.types import (
    FunctionCallMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    Message,
    Reset,
    RespondNow,
    ResponseFormat,
    TextMessage,
)
from agnext.chat.utils import convert_messages_to_llm_messages
from agnext.core import AgentRuntime, CancellationToken


class ChatCompletionAgent(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        system_messages: List[SystemMessage],
        model_client: ModelClient,
        function_executor: FunctionExecutor | None = None,
    ) -> None:
        super().__init__(name, description, runtime)
        self._system_messages = system_messages
        self._client = model_client
        self._chat_messages: List[Message] = []
        self._function_executor = function_executor

    @message_handler(TextMessage)
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        # Add a user message.
        self._chat_messages.append(message)

    @message_handler(Reset)
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        # Reset the chat messages.
        self._chat_messages = []

    @message_handler(RespondNow)
    async def on_respond_now(
        self, message: RespondNow, cancellation_token: CancellationToken
    ) -> TextMessage | FunctionCallMessage:
        # Get function signatures.
        function_signatures: List[FunctionSignature] = (
            [] if self._function_executor is None else list(self._function_executor.function_signatures)
        )

        # Get a response from the model.
        response = await self._client.create(
            self._system_messages + convert_messages_to_llm_messages(self._chat_messages, self.name),
            functions=function_signatures,
            json_output=message.response_format == ResponseFormat.json_object,
        )

        # If the agent has function executor, and the response is a list of
        # tool calls, iterate with itself until we get a response that is not a
        # list of tool calls.
        while (
            self._function_executor is not None
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
                self._system_messages + convert_messages_to_llm_messages(self._chat_messages, self.name),
                functions=function_signatures,
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
        self._chat_messages.append(final_response)

        # Return the response.
        return final_response

    @message_handler(FunctionCallMessage)
    async def on_tool_call_message(
        self, message: FunctionCallMessage, cancellation_token: CancellationToken
    ) -> FunctionExecutionResultMessage:
        if self._function_executor is None:
            raise ValueError("Function executor is not set.")

        # Add a tool call message.
        self._chat_messages.append(message)

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
            future = self.execute_function(function_call.name, arguments, function_call.id)
            # Append the async result.
            execution_futures.append(future)
        if execution_futures:
            # Wait for all async results.
            execution_results = await asyncio.gather(*execution_futures)
            # Add the results.
            for execution_result, call_id in execution_results:
                results.append(FunctionExecutionResult(content=execution_result, call_id=call_id))

        # Create a tool call result message.
        tool_call_result_msg = FunctionExecutionResultMessage(content=results, source=self.name)

        # Add tool call result message.
        self._chat_messages.append(tool_call_result_msg)

        # Return the results.
        return tool_call_result_msg

    async def execute_function(self, name: str, args: Dict[str, Any], call_id: str) -> Tuple[str, str]:
        if self._function_executor is None:
            raise ValueError("Function executor is not set.")
        try:
            result = await self._function_executor.execute_function(name, args)
        except Exception as e:
            result = f"Error: {str(e)}"
        return (result, call_id)

    def save_state(self) -> Mapping[str, Any]:
        return {
            "description": self.description,
            "chat_messages": self._chat_messages,
            "system_messages": self._system_messages,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._chat_messages = state["chat_messages"]
        self._system_messages = state["system_messages"]
        self._description = state["description"]
