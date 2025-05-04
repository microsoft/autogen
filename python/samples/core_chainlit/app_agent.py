from typing import List, cast
import chainlit as cl
import yaml

import asyncio
from dataclasses import dataclass

from autogen_core import (
    AgentId,
    FunctionCall,
    MessageContext,
    SingleThreadedAgentRuntime,
    ClosureAgent,
    ClosureContext,
    TopicId,
    TypeSubscription
)
from autogen_core.models import (
    ChatCompletionClient,
    UserMessage,
)

from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import BufferedChatCompletionContext
from SimpleAssistantAgent import SimpleAssistantAgent, StreamResult 

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")
CLOSURE_AGENT_TYPE = "collect_result_agent"

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

"""
# Function called when closure agent receives message. It put the messages to the output queue
async def output_result(_agent: ClosureContext, message: StreamResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))  # type: ignore
    ui_resp = cast(cl.Message, cl.user_session.get("output_msg"))
    if (message.type == "chunk"):
        print( "sending chunk " + message.value + " to cl")
        await ui_resp.stream_token(message.value)
    else:
        print( "sending the complete message " )
        await ui_resp.send()
"""

# Function called when closure agent receives message. It put the messages to the output queue
async def output_result(_agent: ClosureContext, message: StreamResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))  # type: ignore
    print( "AAAA Adding " + message.value + "to queue")
    await queue.put(message)

@cl.step(type="tool")  # type: ignore
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

@cl.on_chat_start  # type: ignore
async def start_chat() -> None:

    # Load model configuration and create the model client.
    with open("model_config.yaml", "r") as f:
        model_config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(model_config)
    context = BufferedChatCompletionContext(buffer_size=10)

    # Create a runtime and save to chainlit session
    runtime = SingleThreadedAgentRuntime()
    cl.user_session.set("run_time", runtime) # type: ignore
    
    # Create tools
    tools: List[Tool] = [FunctionTool(get_weather, description="Get weather tool.")]

    # Create a queue for output stream data and save to chainlit session
    queue_stream = asyncio.Queue[StreamResult]()
    cl.user_session.set("queue_stream", queue_stream) # type: ignore

    # Create the assistant agent with the get_weather tool.
    await SimpleAssistantAgent.register(runtime, "weather_agent", lambda: SimpleAssistantAgent(
        name="weather_agent",
        tool_schema=tools,
        model_client=model_client,
        system_message="You are a helpful assistant",
        context=context,
        model_client_stream=True,  # Enable model client streaming.
        reflect_on_tool_use=True,  # Reflect on tool use.
    ))

    # Register the Closure Agent to process streaming chunks from agents by exeucting the output_result 
    # function, whihc sends the stream response to the output queue 
    await ClosureAgent.register_closure(
        runtime, CLOSURE_AGENT_TYPE, output_result, subscriptions=lambda:[TypeSubscription(topic_type=TASK_RESULTS_TOPIC_TYPE, agent_type=CLOSURE_AGENT_TYPE)] 
    )

    runtime.start()  # Start processing messages in the background.

@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Construct the response message for the user message received.
    ui_resp = cl.Message(content="")

    # Get the runtime and queue from the session 
    runtime = cast(SingleThreadedAgentRuntime, cl.user_session.get("run_time"))
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))

    output_msg = cl.Message(content="")
    cl.user_session.set("output_msg", output_msg) # type: ignore

    # Send message to the Weather Assistant Agent
    task1 = asyncio.create_task( runtime.send_message(UserMessage(content=message.content, source="User"), AgentId("weather_agent", "default")))

    print("AAAA After creating the task")
    # Consume items from the response queue until the stream ends or an error occurs
    while True:
        print("AAAA read from queue")
        chunk = await queue.get()
        if (chunk.type == "chunk"):
            print( "sending chunk " + chunk.value + " to cl")
            await ui_resp.stream_token(chunk.value)
        else:
            print( "sending the complete message " )
            await ui_resp.send()
            break;
    print("AAAA After loop")
    await task1
    print("AAAA await task1")