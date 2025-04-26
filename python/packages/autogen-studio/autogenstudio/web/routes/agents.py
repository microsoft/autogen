# api/routes/agents.py
import asyncio
from typing import Dict, List

from pydantic import BaseModel
from autogen_agentchat.base._task import TaskResult
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...datamodel import Agent
from ...gallery.builder import create_default_gallery
from ..deps import get_db

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import MessageFactory, BaseChatMessage


router = APIRouter()



@router.get("/")
async def list_agents(user_id: str, db=Depends(get_db)) -> Dict:
    """List all agents for a user"""
    response = db.get(Agent, filters={"user_id": user_id})

    if not response.data or len(response.data) == 0:
        default_gallery = create_default_gallery()
        default_agent = Agent(user_id=user_id, component=default_gallery.components.agents[0].model_dump())

        db.upsert(default_agent)
        response = db.get(Agent, filters={"user_id": user_id})

    return {"status": True, "data": response.data}


@router.get("/{agent_id}")
async def get_agent(agent_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Get a specific agent"""
    response = db.get(Agent, filters={"id": agent_id, "user_id": user_id})
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": True,  "data": response.data[0]}


@router.post("/")
async def create_agent(agent: Agent, db=Depends(get_db)) -> Dict:
    """Create a new agent"""
    response = db.upsert(agent)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Delete a agent"""
    db.delete(filters={"id": agent_id, "user_id": user_id}, model_class=Agent)
    return {"status": True, "message": "Agent deleted successfully"}

class InvokeInput(BaseModel):
    user_id: str
    messages: List[Dict]



@router.post("/{agent_id}/run")
async def run_agent(agent_id: int, input: InvokeInput, db=Depends(get_db)) -> Dict:
    """Run a agent"""
    agent_response = db.get(Agent, filters={"id": agent_id, "user_id": input.user_id}, return_json=False)
    if not agent_response.status or not agent_response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_model: Agent = agent_response.data[0]
    agent_config = agent_model.component
    agent = BaseChatAgent.load_component(agent_config)
    message_factory = MessageFactory()
    messages: List[BaseChatMessage] = []
    for message in input.messages:
        marshalled_message = message_factory.create(message)
        if isinstance(marshalled_message, BaseChatMessage):
            messages.append(marshalled_message)
        else:
            raise HTTPException(status_code=400, detail="Invalid message type")
    result: TaskResult = await agent.run(task=messages)
    return {"status": True, "data": result}


# # Placeholder for the actual agent execution logic
# async def stream_agent_execution(agent_config: Dict):
#     """
#     Placeholder function to simulate streaming agent execution.
#     Replace this with actual logic to instantiate and run the agent,
#     yielding messages in SSE format.
#     """
#     # 1. Instantiate agent from config (using autogen library)
#     # 2. Define a task/message for the agent
#     # 3. Execute the agent and capture its output
#     # 4. Yield messages in SSE format ("data: message\n\n")

#     # Example placeholder:
#     agent_name = agent_config.get("config", {}).get("name", "Unknown Agent")
#     yield f"data: Starting agent execution for: {agent_name}\n\n"
#     await asyncio.sleep(1)
#     yield "data: Agent processing...\n\n"
#     await asyncio.sleep(2)
#     # Simulate potential errors or specific outputs
#     if "error" in agent_name.lower():
#          yield "event: error\ndata: Simulated agent error\n\n"
#          return # Stop streaming on error example
#     yield f"data: Agent {agent_name} completed task chunk.\n\n"
#     await asyncio.sleep(1)
#     yield "event: complete\ndata: Agent finished.\n\n"

# @router.get("/invoke/{agent_id}", response_class=StreamingResponse)
# async def invoke_agent(agent_id: int, user_id: str, db=Depends(get_db)):
#     """Invoke an agent and stream its output using SSE"""
#     agent_response = db.get(Agent, filters={"id": agent_id, "user_id": user_id}, return_json=False)
#     if not agent_response.status or not agent_response.data:
#         raise HTTPException(status_code=404, detail="Agent not found")

#     agent_model: Agent = agent_response.data[0]
#     # Assuming agent_model.component holds the necessary configuration dictionary
#     agent_config = agent_model.component

#     # Define the SSE stream generator using the placeholder
#     async def event_generator():
#         try:
#             async for message in stream_agent_execution(agent_config):
#                 yield message
#         except Exception as e:
#             # TODO: Use proper logging instead of print
#             print(f"Error during agent execution stream for agent {agent_id}: {e}")
#             # Send an error event to the client
#             yield f"event: error\ndata: Error executing agent: {str(e)}\n\n"

#     return StreamingResponse(event_generator(), media_type="text/event-stream")
