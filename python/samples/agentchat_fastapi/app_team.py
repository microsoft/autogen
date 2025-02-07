import json
import logging
import os
from typing import Any, Awaitable, Callable, Optional

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

model_config_path = "model_config.yaml"
state_path = "team_state.json"
history_path = "team_history.json"

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def root():
    """Serve the chat interface HTML file."""
    return FileResponse("app_team.html")


async def get_team(
    user_input_func: Callable[[str, Optional[CancellationToken]], Awaitable[str]],
) -> RoundRobinGroupChat:
    # Get model client from config.
    async with aiofiles.open(model_config_path, "r") as file:
        model_config = yaml.safe_load(await file.read())
    model_client = ChatCompletionClient.load_component(model_config)
    # Create the team.
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are a helpful assistant.",
    )
    yoda = AssistantAgent(
        name="yoda",
        model_client=model_client,
        system_message="Repeat the same message in the tone of Yoda.",
    )
    user_proxy = UserProxyAgent(
        name="user",
        input_func=user_input_func,  # Use the user input function.
    )
    team = RoundRobinGroupChat(
        [agent, yoda, user_proxy],
    )
    # Load state from file.
    if not os.path.exists(state_path):
        return team
    async with aiofiles.open(state_path, "r") as file:
        state = json.loads(await file.read())
    await team.load_state(state)
    return team


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


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()

    # User input function used by the team.
    async def _user_input(prompt: str, cancellation_token: CancellationToken | None) -> str:
        data = await websocket.receive_json()
        message = TextMessage.model_validate(data)
        return message.content

    try:
        while True:
            # Get user message.
            data = await websocket.receive_json()
            request = TextMessage.model_validate(data)

            try:
                # Get the team and respond to the message.
                team = await get_team(_user_input)
                history = await get_history()
                stream = team.run_stream(task=request)
                async for message in stream:
                    if isinstance(message, TaskResult):
                        continue
                    await websocket.send_json(message.model_dump())
                    if not isinstance(message, UserInputRequestedEvent):
                        # Don't save user input events to history.
                        history.append(message.model_dump())

                # Save team state to file.
                async with aiofiles.open(state_path, "w") as file:
                    state = await team.save_state()
                    await file.write(json.dumps(state))

                # Save chat history to file.
                async with aiofiles.open(history_path, "w") as file:
                    await file.write(json.dumps(history))
                    
            except Exception as e:
                # Send error message to client
                error_message = {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "source": "system"
                }
                await websocket.send_json(error_message)
                # Re-enable input after error
                await websocket.send_json({
                    "type": "UserInputRequestedEvent",
                    "content": "An error occurred. Please try again.",
                    "source": "system"
                })
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Unexpected error: {str(e)}",
                "source": "system"
            })
        except:
            pass


# Example usage
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
