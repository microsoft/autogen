from typing import List, cast
import chainlit as cl
import yaml

import asyncio

from autogen_core import (
    AgentId,
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
from autogen_core.model_context import BufferedChatCompletionContext
from SimpleAssistantAgent import SimpleAssistantAgent, FinalResult 

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

# Function called when closure agent receives message. It put the messages to the output queue
async def output_result(_agent: ClosureContext, message: FinalResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))  # type: ignore
    #print( "Adding " + message.value + "to queue")
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

    # Create a runtime.
    runtime = SingleThreadedAgentRuntime()
    
    # Create tools
    tools: List[Tool] = [FunctionTool(get_weather, description="Get weather tool.")]
    # Create a queue for output stream data
    queue = asyncio.Queue[FinalResult]()

    # Create the assistant agent with the get_weather tool.
    await SimpleAssistantAgent.register(runtime, "weather_agent", lambda: SimpleAssistantAgent(
        name="weather_agent",
        tool_schema=tools,
        model_client=model_client,
        system_message="You are a helpful assistant",
        context=context,
        #model_client_stream=True,  # Enable model client streaming.
        #reflect_on_tool_use=True,  # Reflect on tool use.
    ))

    # Register the Closure Agent, it will place streamed response into the output queue by calling output_result function
    await ClosureAgent.register_closure(
        runtime, CLOSURE_AGENT_TYPE, output_result, subscriptions=lambda:[TypeSubscription(topic_type=TASK_RESULTS_TOPIC_TYPE, agent_type=CLOSURE_AGENT_TYPE)] 
    )
    runtime.start()  # Start processing messages in the background.

    # Save the runtime and output_queue into chainlit user session for later use when messages are processed.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("run_time", runtime) # type: ignore
    cl.user_session.set("output_queue", queue) # type: ignore
    
@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the session data for process messages 
    runtime = cast(SingleThreadedAgentRuntime, cl.user_session.get("run_time"))
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))

    # Send message to the Weather Assistant Agent
    # Construct the response message.
    response = await runtime.send_message(UserMessage(content=message.content, source="User"), AgentId("weather_agent", "default"))
    
    # Forward the reponses inside the output queue to the chainlit UI 
    ui_resp = cl.Message(content="")
    while not queue.empty():
        result = await queue.get()
        if (result.type == "chunk"):
            await ui_resp.stream_token(result.value)
        elif (result.type == "response"):
            await ui_resp.send()