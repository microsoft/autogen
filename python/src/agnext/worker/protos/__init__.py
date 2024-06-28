"""
The :mod:`agnext.worker.protos` module provides Google Protobuf classes for agent-worker communication
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import TYPE_CHECKING

from .agent_worker_pb2 import Event, Message, RegisterAgentType, RpcRequest, RpcResponse, AgentId
from .agent_worker_pb2_grpc import AgentRpcStub

if TYPE_CHECKING:
    from .agent_worker_pb2_grpc import AgentRpcAsyncStub
    __all__ = ["RpcRequest", "RpcResponse", "Event", "RegisterAgentType", "AgentRpcAsyncStub", "AgentRpcStub", "Message", "AgentId"]
else:
    __all__ = ["RpcRequest", "RpcResponse", "Event", "RegisterAgentType", "AgentRpcStub", "Message", "AgentId"]
