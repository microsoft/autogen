"""
The :mod:`autogen_core.worker.protos` module provides Google Protobuf classes for agent-worker communication
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import TYPE_CHECKING

from .agent_worker_pb2 import AgentId, Event, Message, RegisterAgentType, RpcRequest, RpcResponse
from .agent_worker_pb2_grpc import AgentRpcServicer, AgentRpcStub, add_AgentRpcServicer_to_server

if TYPE_CHECKING:
    from .agent_worker_pb2_grpc import AgentRpcAsyncStub

    __all__ = [
        "RpcRequest",
        "RpcResponse",
        "Event",
        "RegisterAgentType",
        "AgentRpcAsyncStub",
        "AgentRpcStub",
        "Message",
        "AgentId",
    ]
else:
    __all__ = ["RpcRequest", "RpcResponse", "Event", "RegisterAgentType", "AgentRpcStub", "Message", "AgentId"]
