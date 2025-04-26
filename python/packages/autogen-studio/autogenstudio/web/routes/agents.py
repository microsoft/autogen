# api/routes/agents.py
import asyncio
import json
from typing import Dict, List, Any, Optional

from pydantic import BaseModel
from autogen_agentchat.base._task import TaskResult
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...datamodel import Agent, LLMCallEventMessage, TeamResult
from ...gallery.builder import create_default_gallery
from ..deps import get_db

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import BaseAgentEvent, MessageFactory, BaseChatMessage
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ChatMessage,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)


router = APIRouter()



@router.get("/")
async def list_agents(user_id: str, db=Depends(get_db)) -> Dict:
    """List all agents for a user"""
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
    messages: List[Dict]



@router.post("/{agent_id}/run")
async def run_agent(agent_id: int, user_id: str, input: InvokeInput, db=Depends(get_db)) -> Dict:
    """Run a agent"""
    agent_response = db.get(Agent, filters={"id": agent_id, "user_id": user_id}, return_json=False)
    if not agent_response.status or not agent_response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_model: Agent = agent_response.data[0]
    agent_config = agent_model.component
    try:
        agent = BaseChatAgent.load_component(agent_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    message_factory = MessageFactory()
    messages: List[BaseChatMessage] = []
    for message in input.messages:
        try: 
          marshalled_message = message_factory.create(message)
          if isinstance(marshalled_message, BaseChatMessage):
              messages.append(marshalled_message)
          else:
              raise HTTPException(status_code=400, detail="Invalid message type")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    try:
        result: TaskResult = await agent.run(task=messages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    values = []
    for message in result.messages:
        formatted_message = format_message(message)
        if formatted_message:
            values.append(formatted_message)
    return {"status": True, "data": values}

def format_message(message: Any) -> Optional[dict]:
    """Format message for WebSocket transmission

    Args:
        message: Message to format

    Returns:
        Optional[dict]: Formatted message or None if formatting fails
    """

    try:
        if isinstance(message, MultiModalMessage):
            message_dump = message.model_dump()

            message_content = []
            for row in message_dump["content"]:
                if isinstance(row, dict) and "data" in row:
                    message_content.append(
                        {
                            "url": f"data:image/png;base64,{row['data']}",
                            "alt": "WebSurfer Screenshot",
                        }
                    )
                else:
                    message_content.append(row)
            message_dump["content"] = message_content

            return {"type": "message", "data": message_dump}

        elif isinstance(message, TeamResult):
            return {
                "type": "result",
                "data": message.model_dump(),
                "status": "complete",
            }
        elif isinstance(message, ModelClientStreamingChunkEvent):
            return {"type": "message_chunk", "data": message.model_dump()}

        elif isinstance(
            message,
            (
                TextMessage,
                StopMessage,
                HandoffMessage,
                ToolCallRequestEvent,
                ToolCallExecutionEvent,
                LLMCallEventMessage,
                ModelClientStreamingChunkEvent,
            ),
        ):
            return {"type": "message", "data": message.model_dump()}

        return None
    except Exception as e:
        return None

@router.post("/{agent_id}/invoke", response_class=StreamingResponse)
async def invoke_agent(agent_id: int, user_id: str, input: InvokeInput, db=Depends(get_db)):
    """Run a agent"""
    agent_response = db.get(Agent, filters={"id": agent_id, "user_id": user_id}, return_json=False)
    if not agent_response.status or not agent_response.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_model: Agent = agent_response.data[0]
    agent_config = agent_model.component
    agent = BaseChatAgent.load_component(agent_config)
    message_factory = MessageFactory()
    messages: List[BaseChatMessage] = []
    for message in input.messages:
        marshalled_message: BaseAgentEvent | BaseChatMessage = message_factory.create(message)
        if isinstance(marshalled_message, BaseChatMessage):
            messages.append(marshalled_message)
        else:
            raise HTTPException(status_code=400, detail="Invalid message type")
    
    async def event_generator():
        async for event in agent.run_stream(task=messages):
            yield json.dumps(format_message(event))
    return StreamingResponse(event_generator(), media_type="text/event-stream")
