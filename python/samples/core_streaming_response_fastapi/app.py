import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List

import aiofiles
import yaml
from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from autogen_core.models import AssistantMessage, ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse


@dataclass
class AgentResponse:
    """
    Represents the final accumulated response content from the LLM agent.
    Note: The 'content' field hold the final response content.
    """

    content: str


@dataclass
class UserRequest:
    """
    Represents the chat history, containing a list of messages.
    Each message is expected to be a dictionary with 'source' and 'content' keys.
    """

    messages: List[Dict[str, str]]


# Runtime for the agent.
runtime = SingleThreadedAgentRuntime()

# Queue for streaming results from the agent back to the request handler
response_queue: asyncio.Queue[str | object] = asyncio.Queue()

# Sentinel object to signal the end of the stream
STREAM_DONE = object()


class MyAgent(RoutedAgent):
    def __init__(self, name: str, model_client: ChatCompletionClient) -> None:
        super().__init__(name)
        self._system_messages = [SystemMessage(content="You are a helpful assistant.")]
        self._model_client = model_client
        self._response_queue = response_queue

    @message_handler
    async def handle_user_message(self, message: UserRequest, ctx: MessageContext) -> AgentResponse:
        accumulated_content = ""  # To store the full response.
        try:
            _message = message.messages
            user_messages: List[LLMMessage] = []
            for m in _message:
                if m["source"] == "user":
                    user_messages.append(UserMessage(content=m["source"], source=m["source"]))
                else:
                    user_messages.append(AssistantMessage(content=m["source"], source=m["source"]))
            # Create a stream of messages to the model client.
            async for i in self._model_client.create_stream(user_messages, cancellation_token=ctx.cancellation_token):
                if isinstance(i, str):
                    accumulated_content += i
                    await self._response_queue.put(i)
                else:
                    break
            await self._response_queue.put(STREAM_DONE)
            return AgentResponse(content=accumulated_content)
        except Exception as e:
            await self._response_queue.put("ERROR:" + str(e))
            return AgentResponse(content=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Get model client from config.
    async with aiofiles.open("model_config.yaml", "r") as file:
        model_config = yaml.safe_load(await file.read())
    model_client = ChatCompletionClient.load_component(model_config)

    # Register the agent with the runtime.
    await MyAgent.register(
        runtime,
        "simple_agent",
        lambda: MyAgent(
            "myagent",
            model_client=model_client,
        ),
    )

    # Start the agent runtime.
    runtime.start()
    yield
    await runtime.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/chat/completions")
async def chat_completions_stream(request: Request):
    json_data = await request.json()
    messages = json_data.get("messages", "")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="Invalid input: 'messages' must be a list.")
    user_request = UserRequest(messages=messages)  # type: ignore

    async def response_stream() -> AsyncGenerator[str, None]:
        task1 = asyncio.create_task(runtime.send_message(user_request, AgentId("simple_agent", "default")))
        # Consume items from the response queue until the stream ends or an error occurs
        while True:
            item = await response_queue.get()
            if item is STREAM_DONE:
                print(f"{time.time():.2f} - MAIN: Received STREAM_DONE. Exiting loop.")
                break
            elif isinstance(item, str) and item.startswith("ERROR:"):
                print(f"{time.time():.2f} - MAIN: Received error message from agent: {item}")
                break
            else:
                yield json.dumps({"content": item}) + "\n"

        # Wait for the task to finish.
        await task1

    return StreamingResponse(response_stream(), media_type="text/plain")  # type: ignore


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8501)
