import asyncio
import logging
import signal
from typing import Optional, Sequence

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from ._json_rpc import JsonRpcRequest, JsonRpcResponse
from ._worker_runtime_host_servicer import HttpWorkerAgentRuntimeHostServicer
from ._worker_runtime import subscription_from_json, subscription_to_json

logger = logging.getLogger("autogen_core")


class HttpWorkerAgentRuntimeHost:
    """
    Wraps a FastAPI app that uses `HttpWorkerAgentRuntimeHostServicer` behind the scenes.
    Provides endpoints (REST + WebSocket) for agent workers to connect and register, add subscriptions, etc.
    """

    def __init__(self, address: str = "127.0.0.1", port: int = 8000):
        self._address = address
        self._port = port
        self._app = FastAPI()
        self._servicer = HttpWorkerAgentRuntimeHostServicer()
        self._runner_task: Optional[asyncio.Task] = None
        self._server: Optional[uvicorn.Server] = None

        # define routes
        @self._app.websocket("/open_channel")
        async def open_channel(ws: WebSocket, client_id: str):
            # accept connection
            await ws.accept()
            await self._servicer.on_client_connected(client_id, ws)
            try:
                while True:
                    data = await ws.receive_json()
                    await self._servicer.handle_websocket_message(client_id, data)
            except WebSocketDisconnect:
                await self._servicer.on_client_disconnected(client_id)

        @self._app.post("/rpc")
        async def rpc_handler(request: Request):
            client_id = request.headers.get("x-client-id")
            logger.info(f"Received RPC request from client_id={client_id}")
            if not client_id:
                logger.error("Missing client_id in RPC request")
                return JsonRpcResponse(
                    error={"code": -32000, "message": "Missing client_id header"}, id=None
                ).model_dump()

            req_data = await request.json()
            logger.info(f"RPC request data: {req_data}")
            req = JsonRpcRequest(**req_data)

            try:
                # Agent communication methods
                if req.method == "agent.call":
                    logger.info(f"Processing agent.call from client {client_id}")
                    result = await self._servicer.rpc_agent_call(client_id, **req.params)
                    logger.info(f"Completed agent.call for client {client_id}")
                elif req.method == "agent.publish":
                    logger.info(f"Processing agent.publish from client {client_id}")
                    await self._servicer.rpc_agent_publish(client_id, **req.params)
                    result = None  # notifications ignore result
                    logger.info(f"Completed agent.publish for client {client_id}")

                # Runtime administrative methods
                elif req.method == "runtime.register_agent":
                    logger.info(f"Processing runtime.register_agent from client {client_id}")
                    agent_type = req.params.get("type")
                    if not agent_type:
                        raise ValueError("Missing 'type' in params for runtime.register_agent")
                    await self._servicer.register_agent_type(client_id, agent_type)
                    result = {"ok": True}
                    logger.info(f"Completed runtime.register_agent for client {client_id}")
                elif req.method == "runtime.add_subscription":
                    logger.info(f"Processing runtime.add_subscription from client {client_id}")
                    sub = subscription_from_json(req.params)  # Expects the subscription JSON as params
                    await self._servicer.add_subscription(client_id, sub)
                    result = {"ok": True}
                    logger.info(f"Completed runtime.add_subscription for client {client_id}")
                elif req.method == "runtime.remove_subscription":
                    logger.info(f"Processing runtime.remove_subscription from client {client_id}")
                    sub_id = req.params.get("id")
                    if not sub_id:
                        raise ValueError("Missing 'id' in params for runtime.remove_subscription")
                    await self._servicer.remove_subscription(client_id, sub_id)
                    result = {"ok": True}
                    logger.info(f"Completed runtime.remove_subscription for client {client_id}")
                elif req.method == "runtime.get_subscriptions":
                    logger.info(f"Processing runtime.get_subscriptions from client {client_id}")
                    subs = await self._servicer.get_subscriptions()
                    result = {"subscriptions": [subscription_to_json(s) for s in subs]}
                    logger.info(f"Completed runtime.get_subscriptions for client {client_id}")
                else:
                    logger.error(f"Unknown method {req.method}")
                    raise ValueError(f"Unknown method {req.method}")

                logger.info(f"Sending RPC response for request_id={req.id}")
                return JsonRpcResponse(result=result, id=req.id).model_dump()
            except Exception as ex:
                logger.error(f"Error processing RPC request: {str(ex)}", exc_info=ex)
                return JsonRpcResponse(error={"code": -32000, "message": str(ex)}, id=req.id).model_dump()

    def start(self) -> None:
        if self._runner_task is not None:
            raise RuntimeError("Already started")
        config = uvicorn.Config(self._app, host=self._address, port=self._port, loop="asyncio")
        self._server = uvicorn.Server(config)

        async def run_server():
            if self._server:  # check necessary for type checker
                await self._server.serve()

        self._runner_task = asyncio.create_task(run_server())

    async def stop(self, grace: int = 2) -> None:
        if self._runner_task is None or self._server is None:
            raise RuntimeError("Not started")

        self._server.should_exit = True
        try:
            # Wait for the server task to finish gracefully
            await asyncio.wait_for(self._runner_task, timeout=grace)
        except asyncio.TimeoutError:
            pass

        self._runner_task = None
        self._server = None

    async def stop_when_signal(
        self, grace: int = 5, signals: Sequence[signal.Signals] = (signal.SIGTERM, signal.SIGINT)
    ) -> None:
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def do_stop():
            stop_event.set()

        for s in signals:
            loop.add_signal_handler(s, do_stop)

        await stop_event.wait()
        await self.stop(grace=grace)
