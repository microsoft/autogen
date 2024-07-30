import asyncio
import json
from typing import Any, Coroutine, Dict, List, Mapping, Sequence, Tuple

from agnext.components import (
    FunctionCall,
    TypeRoutedAgent,
    message_handler,
)
from agnext.components.memory import ChatMemory
from agnext.components.models import (
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    SystemMessage,
)
from agnext.components.tools import Tool
from agnext.core import AgentId, CancellationToken

from ..types import (
    FunctionCallMessage,
    Message,
    MultiModalMessage,
    PublishNow,
    Reset,
    RespondNow,
    ResponseFormat,
    TextMessage,
    ToolApprovalRequest,
    ToolApprovalResponse,
)
from ..utils import convert_messages_to_llm_messages


class ChatCompletionAgent(TypeRoutedAgent):
    """An agent implementation that uses the ChatCompletion API to gnenerate
    responses and execute tools.

    Args:
        description (str): The description of the agent.
        system_messages (List[SystemMessage]): The system messages to use for
            the ChatCompletion API.
        memory (ChatMemory[Message]): The memory to store and retrieve messages.
        model_client (ChatCompletionClient): The client to use for the
            ChatCompletion API.
        tools (Sequence[Tool], optional): The tools used by the agent. Defaults
            to []. If no tools are provided, the agent cannot handle tool calls.
            If tools are provided, and the response from the model is a list of
            tool calls, the agent will call itselfs with the tool calls until it
            gets a response that is not a list of tool calls, and then use that
            response as the final response.
        tool_approver (Agent | None, optional): The agent that approves tool
            calls. Defaults to None. If no tool approver is provided, the agent
            will execute the tools without approval. If a tool approver is
            provided, the agent will send a request to the tool approver before
            executing the tools.
    """

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        memory: ChatMemory[Message],
        model_client: ChatCompletionClient,
        tools: Sequence[Tool] = [],
        tool_approver: AgentId | None = None,
    ) -> None:
        super().__init__(description)
        self._description = description
        self._system_messages = system_messages
        self._client = model_client
        self._memory = memory
        self._tools = tools
        self._tool_approver = tool_approver

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        """Handle a text message. This method adds the message to the memory and
        does not generate any message."""
        # Add a user message.
        await self._memory.add_message(message)

    @message_handler()
    async def on_multi_modal_message(self, message: MultiModalMessage, cancellation_token: CancellationToken) -> None:
        """Handle a multimodal message. This method adds the message to the memory
        and does not generate any message."""
        # Add a user message.
        await self._memory.add_message(message)

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        """Handle a reset message. This method clears the memory."""
        # Reset the chat messages.
        await self._memory.clear()

    @message_handler()
    async def on_respond_now(
        self, message: RespondNow, cancellation_token: CancellationToken
    ) -> TextMessage | FunctionCallMessage:
        """Handle a respond now message. This method generates a response and
        returns it to the sender."""
        # Generate a response.
        response = await self._generate_response(message.response_format, cancellation_token)

        # Return the response.
        return response

    @message_handler()
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        """Handle a publish now message. This method generates a response and
        publishes it."""
        # Generate a response.
        response = await self._generate_response(message.response_format, cancellation_token)

        # Publish the response.
        await self.publish_message(response)

    @message_handler()
    async def on_tool_call_message(
        self, message: FunctionCallMessage, cancellation_token: CancellationToken
    ) -> FunctionExecutionResultMessage:
        """Handle a tool call message. This method executes the tools and
        returns the results."""
        if len(self._tools) == 0:
            raise ValueError("No tools available")

        # Add a tool call message.
        await self._memory.add_message(message)

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
            future = self._execute_function(
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
        await self._memory.add_message(tool_call_result_msg)

        # Return the results.
        return tool_call_result_msg

    async def _generate_response(
        self,
        response_format: ResponseFormat,
        cancellation_token: CancellationToken,
    ) -> TextMessage | FunctionCallMessage:
        # Get a response from the model.
        hisorical_messages = await self._memory.get_messages()
        response = await self._client.create(
            self._system_messages + convert_messages_to_llm_messages(hisorical_messages, self.metadata["name"]),
            tools=self._tools,
            json_output=response_format == ResponseFormat.json_object,
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
            response = await self.send_message(
                message=FunctionCallMessage(content=response.content, source=self.metadata["name"]),
                recipient=self.id,
                cancellation_token=cancellation_token,
            )
            # Make an assistant message from the response.
            hisorical_messages = await self._memory.get_messages()
            response = await self._client.create(
                self._system_messages + convert_messages_to_llm_messages(hisorical_messages, self.metadata["name"]),
                tools=self._tools,
                json_output=response_format == ResponseFormat.json_object,
            )

        final_response: Message
        if isinstance(response.content, str):
            # If the response is a string, return a text message.
            final_response = TextMessage(content=response.content, source=self.metadata["name"])
        elif isinstance(response.content, list) and all(isinstance(x, FunctionCall) for x in response.content):
            # If the response is a list of function calls, return a function call message.
            final_response = FunctionCallMessage(content=response.content, source=self.metadata["name"])
        else:
            raise ValueError(f"Unexpected response: {response.content}")

        # Add the response to the chat messages.
        await self._memory.add_message(final_response)

        return final_response

    async def _execute_function(
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

        # Check if the tool needs approval
        if self._tool_approver is not None:
            # Send a tool approval request.
            approval_request = ToolApprovalRequest(
                tool_call=FunctionCall(id=call_id, arguments=json.dumps(args), name=name)
            )
            approval_response = await self.send_message(
                message=approval_request,
                recipient=self._tool_approver,
                cancellation_token=cancellation_token,
            )
            if not isinstance(approval_response, ToolApprovalResponse):
                raise ValueError(f"Expecting {ToolApprovalResponse.__name__}, received: {type(approval_response)}")
            if not approval_response.approved:
                return (f"Error: tool {name} approved, reason: {approval_response.reason}", call_id)

        try:
            result = await tool.run_json(args, cancellation_token)
            result_as_str = tool.return_value_as_string(result)
        except Exception as e:
            result_as_str = f"Error: {str(e)}"
        return (result_as_str, call_id)

    def save_state(self) -> Mapping[str, Any]:
        return {
            "memory": self._memory.save_state(),
            "system_messages": self._system_messages,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._memory.load_state(state["memory"])
        self._system_messages = state["system_messages"]
