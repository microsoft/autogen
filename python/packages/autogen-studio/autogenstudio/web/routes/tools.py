from typing import Literal
from autogen_ext.tools.mcp._config import SseServerParams, StdioServerParams
from autogen_ext.tools.mcp._factory import mcp_server_tools

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class McpToolParams(BaseModel):
    type: Literal["stdio", "sse"]
    server_params: SseServerParams | StdioServerParams


@router.post("/discover")
async def resolve_mcp_tool(params: McpToolParams):
    tools = await mcp_server_tools(params.server_params)
    if not tools:
        raise HTTPException(status_code=400, detail="Failed to retrieve tools")
    return [tool.dump_component() for tool in tools]