import asyncio
import logging
import socket

import pytest
from pydantic import BaseModel

from autogen_ext.runtimes.http import HttpWorkerAgentRuntime, HttpWorkerAgentRuntimeHost
from autogen_core import MessageContext, rpc, RoutedAgent
from autogen_core._serialization import PydanticJsonMessageSerializer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -------- messages ---------------------------------------------------
class Ping(BaseModel):
    content: str = "ping"


class Pong(BaseModel):
    content: str


# -------- callee agent ----------------------------------------------
class CalleeAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Echoes a Ping with a Pong")

    @rpc
    async def on_ping(self, message: Ping, ctx: MessageContext) -> Pong:
        logger.info(f"CalleeAgent received ping message: {message.content}")
        return Pong(content=f"pong: {message.content}")


# -------- test -------------------------------------------------------
@pytest.mark.asyncio
async def test_http_rpc_roundtrip() -> None:
    logger.info("Starting HTTP RPC roundtrip test")
    
    # Allocate an ephemeral free TCP port so the test can run in parallel
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    
    logger.info(f"Using ephemeral port: {port}")

    host = HttpWorkerAgentRuntimeHost(port=port)
    host.start()
    
    # Give the uvicorn server more time to start up
    logger.info("Waiting for uvicorn server to start...")
    await asyncio.sleep(1.0)  # Increased from 0.1s to 1.0s

    logger.info("Initializing callee runtime")
    callee_rt = HttpWorkerAgentRuntime(f"http://127.0.0.1:{port}")
    await callee_rt.register_factory("callee", CalleeAgent)  # maps agent_type -> this runtime
    
    # Register message types with the runtime's serialization registry
    logger.info("Registering message serializers")
    callee_rt.add_message_serializer([
        PydanticJsonMessageSerializer(Ping),
        PydanticJsonMessageSerializer(Pong),
    ])
    
    logger.info("Starting callee runtime")
    await callee_rt.start()
    
    logger.info("Initializing caller runtime")
    caller_rt = HttpWorkerAgentRuntime(f"http://127.0.0.1:{port}")
    
    # Register the same message types with the caller's serialization registry
    logger.info("Registering message serializers for caller")
    caller_rt.add_message_serializer([
        PydanticJsonMessageSerializer(Ping),
        PydanticJsonMessageSerializer(Pong),
    ])
    
    logger.info("Starting caller runtime")
    await caller_rt.start()

    try:
        logger.info("Getting callee agent")
        callee_id = await caller_rt.get("callee")  # AgentId(type="callee", key="default")
        
        logger.info(f"Sending ping message to {callee_id}")
        result: Pong = await caller_rt.send_message(
            Ping(content="hello"), recipient=callee_id
        )
        
        logger.info(f"Received result: {result}")
        assert result.content == "pong: hello"
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=e)
        raise
    finally:
        logger.info("Shutting down runtimes")
        await caller_rt.stop()
        await callee_rt.stop()
        await host.stop()
        logger.info("Test complete")
