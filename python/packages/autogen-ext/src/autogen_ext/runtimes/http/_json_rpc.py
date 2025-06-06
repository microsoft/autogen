from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None
    id: str | int | None  # id == None → notification


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    # exactly one of result / error
    result: Any | None = None
    error: dict[str, Any] | None = None
    id: str | int | None
