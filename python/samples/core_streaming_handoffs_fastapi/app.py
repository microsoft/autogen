import json
import time
import os
import re

from autogen_core import (
    SingleThreadedAgentRuntime,
    TypeSubscription,
    TopicId
)
from autogen_core.models import (
    SystemMessage,
    UserMessage,
    AssistantMessage
)

from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from agent_user import UserAgent
from agent_base import AIAgent

from models import UserTask
from topics import (
    triage_agent_topic_type,
    user_topic_type,
    sales_agent_topic_type,
    issues_and_repairs_agent_topic_type,
)

from tools import (
    execute_order_tool,
    execute_refund_tool,
    look_up_item_tool,
)

from tools_delegate import (
    transfer_to_issues_and_repairs_tool,
    transfer_to_sales_agent_tool,
    transfer_back_to_triage_tool
)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import aiofiles
import yaml
import asyncio


# Runtime for the agent.
runtime = SingleThreadedAgentRuntime()

# Queue for streaming results from the agent back to the request handler
response_queue: asyncio.Queue[str | object] = asyncio.Queue()

# Sentinel object to signal the end of the stream
STREAM_DONE = object()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create chat_history directory if it doesn't exist
    chat_history_dir = "chat_history"
    if not os.path.exists(chat_history_dir):
        os.makedirs(chat_history_dir)

    # Get model client from config.
    async with aiofiles.open("model_config.yaml", "r") as file:
        model_config = yaml.safe_load(await file.read())
    model_client = AzureOpenAIChatCompletionClient.load_component(model_config)

    # Register the triage agent.
    triage_agent_type = await AIAgent.register(
        runtime,
        type=triage_agent_topic_type,  # Using the topic type as the agent type.
        factory=lambda: AIAgent(
            description="A triage agent.",
            system_message=SystemMessage(
                content="You are a customer service bot for ACME Inc. "
                "Introduce yourself. Always be very brief. "
                "Gather information to direct the customer to the right department. "
                "But make your questions subtle and natural."
            ),
            model_client=model_client,
            tools=[],
            delegate_tools=[
                transfer_to_issues_and_repairs_tool,
                transfer_to_sales_agent_tool
            ],
            agent_topic_type=triage_agent_topic_type,
            user_topic_type=user_topic_type,
            response_queue=response_queue
        ),
    )
    # Add subscriptions for the triage agent: it will receive messages published to its own topic only.
    await runtime.add_subscription(TypeSubscription(topic_type=triage_agent_topic_type, agent_type=triage_agent_type.type))

    # Register the sales agent.
    sales_agent_type = await AIAgent.register(
        runtime,
        type=sales_agent_topic_type,  # Using the topic type as the agent type.
        factory=lambda: AIAgent(
            description="A sales agent.",
            system_message=SystemMessage(
                content="You are a sales agent for ACME Inc."
                "Always answer in a sentence or less."
                "Follow the following routine with the user:"
                "1. Ask them about any problems in their life related to catching roadrunners.\n"
                "2. Casually mention one of ACME's crazy made-up products can help.\n"
                " - Don't mention price.\n"
                "3. Once the user is bought in, drop a ridiculous price.\n"
                "4. Only after everything, and if the user says yes, "
                "tell them a crazy caveat and execute their order.\n"
                ""
            ),
            model_client=model_client,
            tools=[execute_order_tool],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=sales_agent_topic_type,
            user_topic_type=user_topic_type,
            response_queue=response_queue
        ),
    )
    # Add subscriptions for the sales agent: it will receive messages published to its own topic only.
    await runtime.add_subscription(TypeSubscription(topic_type=sales_agent_topic_type, agent_type=sales_agent_type.type))

    # Register the issues and repairs agent.
    issues_and_repairs_agent_type = await AIAgent.register(
        runtime,
        type=issues_and_repairs_agent_topic_type,  # Using the topic type as the agent type.
        factory=lambda: AIAgent(
            description="An issues and repairs agent.",
            system_message=SystemMessage(
                content="You are a customer support agent for ACME Inc."
                "Always answer in a sentence or less."
                "Follow the following routine with the user:"
                "1. First, ask probing questions and understand the user's problem deeper.\n"
                " - unless the user has already provided a reason.\n"
                "2. Propose a fix (make one up).\n"
                "3. ONLY if not satisfied, offer a refund.\n"
                "4. If accepted, search for the ID and then execute refund."
            ),
            model_client=model_client,
            tools=[
                execute_refund_tool,
                look_up_item_tool,
            ],
            delegate_tools=[transfer_back_to_triage_tool],
            agent_topic_type=issues_and_repairs_agent_topic_type,
            user_topic_type=user_topic_type,
            response_queue=response_queue
        ),
    )
    # Add subscriptions for the issues and repairs agent: it will receive messages published to its own topic only.
    await runtime.add_subscription(
        TypeSubscription(topic_type=issues_and_repairs_agent_topic_type, agent_type=issues_and_repairs_agent_type.type)
    )

    # Register the user agent.
    user_agent_type = await UserAgent.register(
        runtime,
        type=user_topic_type,
        factory=lambda: UserAgent(
            description="A user agent.",
            user_topic_type=user_topic_type,
            agent_topic_type=triage_agent_topic_type,
            response_queue=response_queue,
            stream_done = STREAM_DONE
        )
    )
    # Add subscriptions for the user agent: it will receive messages published to its own topic only.
    await runtime.add_subscription(TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type))

    # Start the agent runtime.
    runtime.start()
    yield
    await runtime.stop()


app = FastAPI(lifespan=lifespan)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    # Serve the index.html file
    return FileResponse('static/index.html')


@app.post("/chat/completions")
async def chat_completions_stream(request: Request):
    json_data = await request.json()
    message = json_data.get("message", "")
    conversation_id = json_data.get("conversation_id", "conv_id")

    if not isinstance(message, str):
        raise HTTPException(status_code=400, detail="Invalid input: 'message' must be a string.")
    
    if not isinstance(conversation_id, str):
        raise HTTPException(status_code=400, detail="Invalid input: 'conversation_id' must be a string.")

    # Validate conversation_id to prevent path traversal attacks
    if not re.match(r'^[A-Za-z0-9_-]+$', conversation_id):
        raise HTTPException(status_code=400, detail="Invalid input: 'conversation_id' contains invalid characters.")

    chat_history_dir = "chat_history"
    base_dir = os.path.abspath(chat_history_dir)
    full_path = os.path.normpath(os.path.join(base_dir, f"history-{conversation_id}.json"))
    if not full_path.startswith(base_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid input: 'conversation_id' leads to invalid path.")
    chat_history_file = full_path
    
    messages = []
    # Initialize chat_history and route_agent with default values
    chat_history = {} 
    route_agent = triage_agent_topic_type

    # Load chat history if it exists.
    # Chat history is saved inside the UserAgent. Use redis if possible.
    # There may be a better way to do this.
    if os.path.exists(chat_history_file):
        context = BufferedChatCompletionContext(buffer_size=15)
        try:
            async with aiofiles.open(chat_history_file, "r") as f:
                content = await f.read()
                if content: # Check if file is not empty
                    chat_history = json.loads(content)
                    await context.load_state(chat_history) # Load state only if history is loaded
                    loaded_messages = await context.get_messages()
                    if loaded_messages:
                        messages = loaded_messages
                        last_message = messages[-1]
                        if isinstance(last_message, AssistantMessage) and isinstance(last_message.source, str):
                            route_agent = last_message.source
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {chat_history_file}. Starting with empty history.")
            # Reset to defaults if loading fails
            messages = []
            route_agent = triage_agent_topic_type
            chat_history = {}
        except Exception as e:
            print(f"Error loading chat history for {conversation_id}: {e}")
            # Reset to defaults on other errors
            messages = []
            route_agent = triage_agent_topic_type
            chat_history = {}
    # else: route_agent remains the default triage_agent_topic_type if file doesn't exist

    messages.append(UserMessage(content=message,source="User"))

    

    async def response_stream() -> AsyncGenerator[str, None]:
        task1 = asyncio.create_task(runtime.publish_message(
            UserTask(context=messages),
            topic_id=TopicId(type=route_agent, source=conversation_id), # Explicitly use 'type' parameter
        ))
        # Consume items from the response queue until the stream ends or an error occurs
        while True:
            item = await response_queue.get()
            if item is STREAM_DONE:
                print(f"{time.time():.2f} - MAIN: Received STREAM_DONE. Exiting loop.")
                break
            elif isinstance(item, str) and item.startswith("ERROR:"):
                print(f"{time.time():.2f} - MAIN: Received error message from agent: {item}")
                break
            # Ensure item is serializable before yielding
            else:
                yield json.dumps({"content": item}) + "\n"

        # Wait for the task to finish.
        await task1

    return StreamingResponse(response_stream(), media_type="text/plain")  # type: ignore


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8501)



