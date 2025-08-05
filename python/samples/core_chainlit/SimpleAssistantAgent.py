from typing import AsyncGenerator, List, Optional
import asyncio
import json
from dataclasses import dataclass

from autogen_core import (
    CancellationToken,
    DefaultTopicId,
    FunctionCall,
    message_handler,
    MessageContext,
    RoutedAgent,
    TopicId
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

from autogen_core.tools import Tool
from pydantic import BaseModel

@dataclass
class Message:
    content: str

class StreamResult(BaseModel):
    content: str | CreateResult | AssistantMessage
    source: str

class GroupChatMessage(BaseModel):
    body: UserMessage

class RequestToSpeak(BaseModel):
    pass

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")

class SimpleAssistantAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        system_message: str,
        #context: MessageContext,
        model_client: ChatCompletionClient,
        tool_schema: List[Tool] = [],
        model_client_stream: bool = False,
        reflect_on_tool_use: bool | None = None,
        group_chat_topic_type: str = "Default",
    ) -> None:
        super().__init__(name)
        self._system_message = SystemMessage(content=system_message)
        self._model_client = model_client
        self._tools = tool_schema
        #self._model_context = context 
        self._model_client_stream = model_client_stream
        self._reflect_on_tool_use = reflect_on_tool_use
        self._group_chat_topic_type = group_chat_topic_type
        self._chat_history: List[LLMMessage] = []

    async def _call_model_client(
        self, cancellation_token: CancellationToken
    ) -> AsyncGenerator[str | CreateResult, None]:
        # Call the LLM model to process the message 
        model_result = None
        async for chunk in self._model_client.create_stream(
            messages=[self._system_message] + self._chat_history,
            tools=self._tools,
            cancellation_token=cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
            elif isinstance(chunk, str):
                yield chunk
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
        
        if model_result is None:    # No final result in model client respons
            raise RuntimeError("No final model result in streaming mode.")

        yield model_result
        return

    async def _execute_tool_call(
        self, call: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        # Find the tool by name.
        tool = next((tool for tool in self._tools if tool.name == call.name), None)
        assert tool is not None

        # Run the tool and capture the result.
        try:
            arguments = json.loads(call.arguments)
            result = await tool.run_json(arguments, cancellation_token, call_id=call.id)
            return FunctionExecutionResult(
                call_id=call.id, content=tool.return_value_as_string(result), is_error=False, name=tool.name
            )
        except Exception as e:
            return FunctionExecutionResult(call_id=call.id, content=str(e), is_error=True, name=tool.name)

    @message_handler
    async def handle_user_message(self, message: UserMessage, ctx: MessageContext) -> Message:

        # Append the message to chat history.
        self._chat_history.append(
           message 
        )

        # Add message to model context.
        # await self._model_context.add_message(UserMessage(content=message.content, source="User"))
        model_result: Optional[CreateResult] = None

        async for chunk in self._call_model_client(
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
            elif isinstance(chunk, str):
                # foward the stream tokent to the Queue
                await self.runtime.publish_message(StreamResult(content=chunk, source=self.id.type), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result is None:    # No final result in model client respons
            raise RuntimeError("No final model result in streaming mode.")

        # Add the first model create result to the session.
        self._chat_history.append(AssistantMessage(content=model_result.content, source=self.id.type))

        if isinstance(model_result.content, str):    # No tools, return the result
            await self.runtime.publish_message(StreamResult(content=model_result, source=self.id.type), topic_id=task_results_topic_id)
            return (Message(content= model_result.content))

        # Execute the tool calls.
        assert isinstance(model_result.content, list) and all(
            isinstance(call, FunctionCall) for call in model_result.content
        )
        results = await asyncio.gather(
            *[self._execute_tool_call(call, ctx.cancellation_token) for call in model_result.content]
        )

        # Add the function execution results to the session.
        self._chat_history.append(FunctionExecutionResultMessage(content=results))

        #if (not self._reflect_on_tool_use):
        #    return Message(content=model_result.content)
        
        # Run the chat completion client again to reflect on the history and function execution results.
        #model_result = None
        model_result2: Optional[CreateResult] = None
        async for chunk in self._call_model_client(
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result2 = chunk
            elif isinstance(chunk, str):
                # foward the stream tokent to the Queue
                await self.runtime.publish_message(StreamResult(content=chunk, source=self.id.type), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result2 is None:
            raise RuntimeError("No final model result in streaming mode.")
        assert model_result2.content is not None 
        assert isinstance(model_result2.content, str)

        await self.runtime.publish_message(StreamResult(content=model_result2, source=self.id.type), topic_id=task_results_topic_id)

        return Message(content=model_result2.content)

    # Message handler for Group chat message. It just add the message to the agent message history.
    # The message will be processed when the agent receives the RequestToSpeak. 
    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend(
            [
                UserMessage(content=f"Transferred to {message.body.source}", source="system"),
                message.body,
            ]
        )

    # Message handler for request to speaker message.
    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        #print(f"### {self.id.type}: ")
        self._chat_history.append(
            UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system")
        )

        # Run the chat completion client again to reflect on the history and function execution results.
        model_result: Optional[CreateResult] = None
        async for chunk in self._call_model_client(
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
                await self.runtime.publish_message(StreamResult(content=model_result, source=self.id.type), topic_id=task_results_topic_id)
            elif isinstance(chunk, str):
                # foward the stream tokent to the Queue
                await self.runtime.publish_message(StreamResult(content=chunk, source=self.id.type), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result is None:
            raise RuntimeError("No final model result in streaming mode.")

        assert isinstance(model_result.content, str)
        assert model_result.content is not None

        self._chat_history.append(AssistantMessage(content=model_result.content, source=self.id.type))
        #print(model_result.content, flush=True)
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=model_result.content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )