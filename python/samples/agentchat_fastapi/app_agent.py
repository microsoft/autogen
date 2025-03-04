import json
import os
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
        state = await agent.save_state()
        async with aiofiles.open(state_path, "w") as file:
            await file.write(json.dumps(state))

        # Save chat history to file.
        history = await get_history()
        history.append(request.model_dump())
        history.append(response.chat_message.model_dump())
        async with aiofiles.open(history_path, "w") as file:
            await file.write(json.dumps(history))

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
