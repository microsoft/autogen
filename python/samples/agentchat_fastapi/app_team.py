import os
import aiofiles
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import TaskResult
from autogen_core.models import ChatCompletionClient
import json
import yaml

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

async def get_team() -> RoundRobinGroupChat:
    # Get model client from config.
    with open(model_config_path, "r") as file:
        model_config = yaml.safe_load(file)
    model_client = ChatCompletionClient.load_component(model_config) 
    # Create the team.
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are a helpful assistant.",
    )
    critic = AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message="You provide feedback. Respond with 'APPROVE' to approve if all feedbacks are addressed.",
    )
    # user_proxy = UserProxyAgent(
    #     name="user_proxy",
    # )
    termination_condition = TextMentionTermination("APPROVE")
    team = RoundRobinGroupChat(
        # [agent, critic, user_proxy],
        [agent, critic],
        termination_condition=termination_condition,
    )
    # Load state from file.
    if not os.path.exists(state_path):
        return team
    async with aiofiles.open(state_path, "r") as file:
        state = json.loads(await file.read())
    await team.load_state(state)
    return team


async def get_history():
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())


@app.get("/history", response_model=list[TextMessage])
async def history():
    try:
        return await get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Get user message.
            data = await websocket.receive_json()
            request = TextMessage.model_validate(data)

            # Get the team and respond to the message.
            team = await get_team()
            history = await get_history()
            stream = team.run_stream(task=request)
            async for message in stream:
                if isinstance(message, TaskResult):
                    continue
                if message.source != request.source:
                    await websocket.send_json(message.model_dump())
                history.append(message.model_dump())

            # Save team state to file.
            async with aiofiles.open(state_path, "w") as file:
                state = await team.save_state()
                await file.write(json.dumps(state))
        
            # Save chat history to file.
            async with aiofiles.open(history_path, "w") as file:
                await file.write(json.dumps(history))
    except WebSocketDisconnect:
        print("websocket disconnected")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Example usage
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
