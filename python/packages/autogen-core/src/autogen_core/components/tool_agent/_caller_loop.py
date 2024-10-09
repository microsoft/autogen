import asyncio
from typing import List

from ...base import AgentId, AgentRuntime, BaseAgent, CancellationToken
from ...components import FunctionCall
from ..models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
)
from ..tools import Tool, ToolSchema
from ._tool_agent import ToolException


async def tool_agent_caller_loop(
    caller: BaseAgent | AgentRuntime,
    tool_agent_id: AgentId,
    model_client: ChatCompletionClient,
    input_messages: List[LLMMessage],
    tool_schema: List[ToolSchema] | List[Tool],
    cancellation_token: CancellationToken | None = None,
    caller_source: str = "assistant",
) -> List[LLMMessage]:
    """Start a caller loop for a tool agent. This function sends messages to the tool agent
    and the model client in an alternating fashion until the model client stops generating tool calls.

    Args:
        tool_agent_id (AgentId): The Agent ID of the tool agent.
        input_messages (List[LLMMessage]): The list of input messages.
        model_client (ChatCompletionClient): The model client to use for the model API.
        tool_schema (List[Tool | ToolSchema]): The list of tools that the model can use.

    Returns:
        List[LLMMessage]: The list of output messages created in the caller loop.
    """

    generated_messages: List[LLMMessage] = []

    # Get a response from the model.
    response = await model_client.create(input_messages, tools=tool_schema, cancellation_token=cancellation_token)
    # Add the response to the generated messages.
    generated_messages.append(AssistantMessage(content=response.content, source=caller_source))

    # Keep iterating until the model stops generating tool calls.
    while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
        # Execute functions called by the model by sending messages to tool agent.
        results: List[FunctionExecutionResult | BaseException] = await asyncio.gather(
            *[
                caller.send_message(
                    message=call,
                    recipient=tool_agent_id,
                    cancellation_token=cancellation_token,
                )
                for call in response.content
            ],
            return_exceptions=True,
        )
        # Combine the results into a single response and handle exceptions.
        function_results: List[FunctionExecutionResult] = []
        for result in results:
            if isinstance(result, FunctionExecutionResult):
                function_results.append(result)
            elif isinstance(result, ToolException):
                function_results.append(FunctionExecutionResult(content=f"Error: {result}", call_id=result.call_id))
            elif isinstance(result, BaseException):
                raise result  # Unexpected exception.
        generated_messages.append(FunctionExecutionResultMessage(content=function_results))
        # Query the model again with the new response.
        response = await model_client.create(
            input_messages + generated_messages, tools=tool_schema, cancellation_token=cancellation_token
        )
        generated_messages.append(AssistantMessage(content=response.content, source=caller_source))

    # Return the generated messages.
    return generated_messages
