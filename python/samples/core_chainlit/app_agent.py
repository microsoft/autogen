from typing import List, cast

import chainlit as cl
import yaml

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
    message_handler,
    CancellationToken
)
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage
)
from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import AssistantMessage, ChatCompletionClient, SystemMessage, UserMessage


@dataclass
class Message:
    content: str
    source: str


class WeatherAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tool_schema: List[Tool]) -> None:
        super().__init__("An agent with a weather tool")
        self._system_messages: List[LLMMessage] = [SystemMessage(content="You are a helpful AI assistant.")]
        self._model_client = model_client
        self._tools = tool_schema
        self._model_context = BufferedChatCompletionContext(buffer_size=5)

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        # Create a session of messages.
        session: List[LLMMessage] = self._system_messages + [UserMessage(content=message.content, source="user")]

        # Add message to model context.
        await self._model_context.add_message(UserMessage(content=message.content, source="user"))

        # Run the chat completion with the tools.
        create_result = await self._model_client.create(
            messages=session,
            tools=self._tools,
            cancellation_token=ctx.cancellation_token,
        )

        # If there are no tool calls, return the result.
        if isinstance(create_result.content, str):
            return Message(content=create_result.content)
        assert isinstance(create_result.content, list) and all(
            isinstance(call, FunctionCall) for call in create_result.content
        )

        # Add the first model create result to the session.
        session.append(AssistantMessage(content=create_result.content, source="assistant"))

        # Execute the tool calls.
        results = await asyncio.gather(
            *[self._execute_tool_call(call, ctx.cancellation_token) for call in create_result.content]
        )

        # Add the function execution results to the session.
        session.append(FunctionExecutionResultMessage(content=results))

        # Run the chat completion again to reflect on the history and function execution results.
        create_result = await self._model_client.create(
            messages=session,
            cancellation_token=ctx.cancellation_token,
        )
        assert isinstance(create_result.content, str)

        # Return the result as a message.
        return Message(content=create_result.content)

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


@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="Greetings",
            message="Hello! What can you help me with today?",
        ),
        cl.Starter(
            label="Weather",
            message="Find the weather in New York City.",
        ),
    ]


@cl.step(type="tool")  # type: ignore
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."


@cl.on_chat_start  # type: ignore
async def start_chat() -> None:
    # Load model configuration and create the model client.
    with open("model_config.yaml", "r") as f:
        model_config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(model_config)

    # Create the agent with the get_weather tool.
#    assistant = WeatherAgent(
 #       model_client = model_client,
  #      tool_schema = [get_weather]
   # )

    # Register the weather agent to runtime
    runtime = SingleThreadedAgentRuntime()
    await WeatherAgent.register(runtime, "weather_agent", lambda: WeatherAgent("weather_agent"))
    
    runtime.start()  # Start processing messages in the background.

    # Set the assistant agent in the user session.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("agent", WeatherAgent)  # type: ignore
    

    


@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the assistant agent from the user session.
    agent = cast(WeatherAgent, cl.user_session.get("agent"))  # type: ignore
    # Construct the response message.
    response = cl.Message(content="")
    async for msg in agent.on_message(
        message=[Message(content=message.content, source="user")],
        ctx=prompt_history,
    ):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user.
            await response.stream_token(msg.content)
        elif isinstance(msg, Response):
            # Done streaming the model client response. Send the message.
            await response.send()
