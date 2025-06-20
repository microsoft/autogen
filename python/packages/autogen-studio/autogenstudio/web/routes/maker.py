# api/routes/maker.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from autogenstudio.maker.tool import ToolMaker, ToolMakerEvent, ComponentModel
import json
import asyncio

router = APIRouter()

@router.websocket("/maker/tool")
async def maker_tool_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming tool creation events and final tool config.
    Receives a JSON message: {"description": "..."}
    Streams ToolMakerEvent and final ComponentModel as JSON.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        description = payload.get("description")
        if not description:
            await websocket.send_json({"error": "Missing 'description'"})
            await websocket.close()
            return
        tool_maker = ToolMaker()
        async for event in tool_maker.run_stream(description):
            # Serialize Pydantic models to dict and send as JSON
            if isinstance(event, ToolMakerEvent):
                await websocket.send_json({"event": event.model_dump()})
            elif isinstance(event, ComponentModel):
                await websocket.send_json({"component": event.model_dump()})
            await asyncio.sleep(0)  # Yield control
        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
