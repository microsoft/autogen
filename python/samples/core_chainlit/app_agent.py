from typing import List, cast

import chainlit as cl
import yaml

#from autogen_agentchat.agents import AssistantAgent
#from autogen_agentchat.base import Response
#from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage

from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient

from dataclasses import dataclass

from autogen_core import SingleThreadedAgentRuntime

from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler


@dataclass
class MyMessageType:
    content: str


class AssistantAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("AssistantAgent")

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.id.type} received message: {message.content}")



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

    ##replace
    # Create the assistant agent with the get_weather tool.
    assistant = AssistantAgent(
        name="assistant",
        tools=[get_weather],
        model_client=model_client,
        system_message="You are a helpful assistant",
        model_client_stream=True,  # Enable model client streaming.
        reflect_on_tool_use=True,  # Reflect on tool use.
    )

    # Register the assistant agent to runtime
    runtime = SingleThreadedAgentRuntime()
    await AssistantAgent.register(runtime, "my_assistant", lambda: AssistantAgent("my_assistant"))
    
    runtime.start()  # Start processing messages in the background.
    
    await runtime.send_message(MyMessageType("Hello, World!"), AgentId("my_agent", "default"))
    await runtime.send_message(MyMessageType("Hello, World!"), AgentId("my_assistant", "default"))
    await runtime.stop()  # Stop processing messages in the background.


    # Set the assistant agent in the user session.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("agent", assistant)  # type: ignore

    

    


@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the assistant agent from the user session.
    agent = cast(AssistantAgent, cl.user_session.get("agent"))  # type: ignore
    # Construct the response message.
    response = cl.Message(content="")
    async for msg in agent.on_messages_stream(
        messages=[TextMessage(content=message.content, source="user")],
        cancellation_token=CancellationToken(),
    ):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user.
            await response.stream_token(msg.content)
        elif isinstance(msg, Response):
            # Done streaming the model client response. Send the message.
            await response.send()
