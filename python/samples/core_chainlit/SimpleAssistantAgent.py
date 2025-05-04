from typing import List, cast, Literal

import asyncio
import json
from dataclasses import dataclass
from typing import List

from autogen_core import (
    AgentId,
    FunctionCall,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    DefaultSubscription,
    DefaultTopicId,
    default_subscription,
    message_handler,
    CancellationToken,
    ClosureAgent,
    ClosureContext,
    TopicId,
    TypeSubscription
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage
)

from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import BufferedChatCompletionContext

@dataclass
class Message:
    content: str

@dataclass
class StreamResult:
    type: str
    value: str

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")

@default_subscription
class SimpleAssistantAgent(RoutedAgent):
    def __init__(self, name: str, model_client: ChatCompletionClient, tool_schema: List[Tool], system_message: str, context: MessageContext, model_client_stream: bool = False, reflect_on_tool_use: bool | None = None) -> None:
        super().__init__(name)
        self._system_messages: List[LLMMessage] = [SystemMessage(content=system_message)]
        self._model_client = model_client
        self._tools = tool_schema
        self._model_context = context 
        self._model_client_stream = model_client_stream
        self._reflect_on_tool_use = reflect_on_tool_use

    @message_handler
    async def handle_message(self, message: UserMessage, ctx: MessageContext) -> Message:
        # Create a session of messages.
        session: List[LLMMessage] = self._system_messages + [UserMessage(content=message.content, source="user")]

        # Add message to model context.
        await self._model_context.add_message(UserMessage(content=message.content, source="user"))
        model_result: Optional[CreateResult] = None

        # Run the chat completion with the tools.
        async for chunk in self._model_client.create_stream(
            messages=session,
            tools=self._tools,
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
            elif isinstance(chunk, str):
		# forward the stream token to the closure agent
                await self.runtime.publish_message(StreamResult("chunk", chunk), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result is None:
            raise RuntimeError("No final model result in streaming mode.")

        # If there are no tool calls, return the result.
        if isinstance(model_result.content, str):
            await self.runtime.publish_message(StreamResult("response", model_result.content), topic_id=task_results_topic_id)
            return Message(content=model_result.content)

        assert isinstance(model_result.content, list) and all(
            isinstance(call, FunctionCall) for call in model_result.content
        )

        # Add the first model create result to the session.
        session.append(AssistantMessage(content=model_result.content, source="assistant"))

        # Execute the tool calls.
        results = await asyncio.gather(
            *[self._execute_tool_call(call, ctx.cancellation_token) for call in model_result.content]
        )

        # Add the function execution results to the session.
        session.append(FunctionExecutionResultMessage(content=results))

        if (not self._reflect_on_tool_use):
            await self.runtime.publish_message(StreamResult("response", results), topic_id=task_results_topic_id)
            return Message(content = results)
        
        # Run the chat completion again to reflect on the history and function execution results.
        model_result = None
        async for chunk in self._model_client.create_stream(
            messages=session,
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
            elif isinstance(chunk, str):
		# foward the stream tokent to the Queue
                await self.runtime.publish_message(StreamResult("chunk", chunk), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result is None:
            raise RuntimeError("No final model result in streaming mode.")

        await self.runtime.publish_message(StreamResult("response", model_result.content), topic_id=task_results_topic_id)
        # Return the result as a message.
        return Message(model_result.content)

    async def _execute_tool_call(
        self, call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        # Find the tool by name.
        tool = next((tool for tool in self._tools if tool.name == call.name), None)
        assert tool is not None

        # Run the tool and capture the result.
        try:
            arguments = json.loads(call.arguments)
            result = await tool.run_json(arguments, cancellation_token)
            return FunctionExecutionResult(
                call_id=call.id, content=tool.return_value_as_string(result), is_error=False, name=tool.name
            )
        except Exception as e:
            return FunctionExecutionResult(call_id=call.id, content=str(e), is_error=True, name=tool.name)