import asyncio
import contextlib
import json
import os
import tempfile
from collections.abc import Mapping
from typing import Any

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def root():
    """Serve the chat interface HTML file."""
    return FileResponse("app_agent.html")

model_config_path = "model_config.yaml"
state_path = "agent_state.json"
history_path = "agent_history.json"

# Serializes the read-modify-write cycles below. Writing with a plain "w" open
# let two overlapping /chat requests interleave their bytes, leaving a file that
# no longer parses and losing the history entries of every request but the last.
_storage_lock = asyncio.Lock()


async def _write_json_atomic(path: str, payload: Any) -> None:
    """Write ``payload`` to ``path`` so a reader never observes a partial file."""
    directory = os.path.dirname(path) or "."
    handle, tmp_path = tempfile.mkstemp(dir=directory, prefix=f".{os.path.basename(path)}.", suffix=".tmp")
    os.close(handle)
    try:
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as file:
            await file.write(json.dumps(payload))
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise


async def save_state(state: Mapping[str, Any]) -> None:
    """Persist the agent state, one writer at a time."""
    async with _storage_lock:
        await _write_json_atomic(state_path, state)


async def append_history(messages: list[dict[str, Any]]) -> None:
    """Append to the chat history without dropping a concurrent append."""
    async with _storage_lock:
        history = await get_history()
        history.extend(messages)
        await _write_json_atomic(history_path, history)


async def get_agent() -> AssistantAgent:
    """Get the assistant agent, load state from file."""
    # Get model client from config.
    async with aiofiles.open(model_config_path, "r") as file:
        model_config = yaml.safe_load(await file.read())
    model_client = ChatCompletionClient.load_component(model_config)
    # Create the assistant agent.
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are a helpful assistant.",
    )
    # Load state from file.
    if not os.path.exists(state_path):
        return agent  # Return agent without loading state.
    async with aiofiles.open(state_path, "r") as file:
        state = json.loads(await file.read())
    await agent.load_state(state)
    return agent


async def get_history() -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())


@app.get("/history")
async def history() -> list[dict[str, Any]]:
    try:
        return await get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/chat", response_model=TextMessage)
async def chat(request: TextMessage) -> TextMessage:
    try:
        # Get the agent and respond to the message.
        agent = await get_agent()
        response = await agent.on_messages(messages=[request], cancellation_token=CancellationToken())

        # Save agent state to file.
        await save_state(await agent.save_state())

        # Save chat history to file.
        await append_history([request.model_dump(), response.chat_message.model_dump()])

        assert isinstance(response.chat_message, TextMessage)
        return response.chat_message
    except Exception as e:
        error_message = {
            "type": "error",
            "content": f"Error: {str(e)}",
            "source": "system"
        }
        raise HTTPException(status_code=500, detail=error_message) from e


# Example usage
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
