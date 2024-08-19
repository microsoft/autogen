import asyncio
import logging
from _collections_abc import AsyncIterator, Iterator
from asyncio import Future, Task
from typing import Any, Dict, Set

import grpc

from .protos import agent_worker_pb2, agent_worker_pb2_grpc

logger = logging.getLogger("agnext")
event_logger = logging.getLogger("agnext.events")


class HostRuntimeServicer(agent_worker_pb2_grpc.AgentRpcServicer):
    """A gRPC servicer that hosts message delivery service for agents."""

    def __init__(self) -> None:
        self._client_id = 0
        self._client_id_lock = asyncio.Lock()
        self._send_queues: Dict[int, asyncio.Queue[agent_worker_pb2.Message]] = {}
        self._agent_type_to_client_id: Dict[str, int] = {}
        self._pending_requests: Dict[int, Dict[str, Future[Any]]] = {}
        self._background_tasks: Set[Task[Any]] = set()

    async def OpenChannel(  # type: ignore
        self,
        request_iterator: AsyncIterator[agent_worker_pb2.Message],
        context: grpc.aio.ServicerContext[agent_worker_pb2.Message, agent_worker_pb2.Message],
    ) -> Iterator[agent_worker_pb2.Message] | AsyncIterator[agent_worker_pb2.Message]:  # type: ignore
        # Aquire the lock to get a new client id.
        async with self._client_id_lock:
            self._client_id += 1
            client_id = self._client_id

        # Register the client with the server and create a send queue for the client.
        send_queue: asyncio.Queue[agent_worker_pb2.Message] = asyncio.Queue()
        self._send_queues[client_id] = send_queue
        logger.info(f"Client {client_id} connected.")

        try:
            # Concurrently handle receiving messages from the client and sending messages to the client.
            # This task will receive messages from the client.
            receiving_task = asyncio.create_task(self._receive_messages(client_id, request_iterator))

            # Return an async generator that will yield messages from the send queue to the client.
            while True:
                message = await send_queue.get()
                # Yield the message to the client.
                try:
                    yield message
                except Exception as e:
                    logger.error(f"Failed to send message to client {client_id}: {e}", exc_info=True)
                    break
            # Wait for the receiving task to finish.
            await receiving_task

        finally:
            # Clean up the client connection.
            del self._send_queues[client_id]
            # Cancel pending requests sent to this client.
            for future in self._pending_requests.pop(client_id, {}).values():
                future.cancel()
            logger.info(f"Client {client_id} disconnected.")

    async def _receive_messages(
        self, client_id: int, request_iterator: AsyncIterator[agent_worker_pb2.Message]
    ) -> None:
        # Receive messages from the client and process them.
        async for message in request_iterator:
            oneofcase = message.WhichOneof("message")
            match oneofcase:
                case "request":
                    request: agent_worker_pb2.RpcRequest = message.request
                    logger.info(f"Received request message: {request}")
                    task = asyncio.create_task(self._process_request(request, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                case "response":
                    response: agent_worker_pb2.RpcResponse = message.response
                    logger.info(f"Received response message: {response}")
                    task = asyncio.create_task(self._process_response(response, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                case "event":
                    event: agent_worker_pb2.Event = message.event
                    logger.info(f"Received event message: {event}")
                    task = asyncio.create_task(self._process_event(event))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                case "registerAgentType":
                    register_agent_type: agent_worker_pb2.RegisterAgentType = message.registerAgentType
                    logger.info(f"Received register agent type message: {register_agent_type}")
                    task = asyncio.create_task(self._process_register_agent_type(register_agent_type, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                case None:
                    logger.warning("Received empty message")

    async def _process_request(self, request: agent_worker_pb2.RpcRequest, client_id: int) -> None:
        # Deliver the message to a client given the target agent type.
        target_client_id = self._agent_type_to_client_id.get(request.target.name)
        if target_client_id is None:
            logger.error(f"Agent {request.target.name} not found, failed to deliver message.")
            return
        target_send_queue = self._send_queues.get(target_client_id)
        if target_send_queue is None:
            logger.error(f"Client {target_client_id} not found, failed to deliver message.")
            return
        await target_send_queue.put(agent_worker_pb2.Message(request=request))

        # Create a future to wait for the response.
        future = asyncio.get_event_loop().create_future()
        self._pending_requests.setdefault(client_id, {})[request.request_id] = future

        # Create a task to wait for the response and send it back to the client.
        send_response_task = asyncio.create_task(self._wait_and_send_response(future, client_id))
        self._background_tasks.add(send_response_task)
        send_response_task.add_done_callback(self._background_tasks.discard)

    async def _wait_and_send_response(self, future: Future[agent_worker_pb2.RpcResponse], client_id: int) -> None:
        response = await future
        message = agent_worker_pb2.Message(response=response)
        send_queue = self._send_queues.get(client_id)
        if send_queue is None:
            logger.error(f"Client {client_id} not found, failed to send response message.")
            return
        await send_queue.put(message)

    async def _process_response(self, response: agent_worker_pb2.RpcResponse, client_id: int) -> None:
        # Setting the result of the future will send the response back to the original sender.
        future = self._pending_requests[client_id].pop(response.request_id)
        future.set_result(response)

    async def _process_event(self, event: agent_worker_pb2.Event) -> None:
        # Deliver the event to all the clients.
        # TODO: deliver based on subscriptions.
        for send_queue in self._send_queues.values():
            await send_queue.put(agent_worker_pb2.Message(event=event))

    async def _process_register_agent_type(
        self, register_agent_type: agent_worker_pb2.RegisterAgentType, client_id: int
    ) -> None:
        # Register the agent type with the host runtime.
        if register_agent_type.type in self._agent_type_to_client_id:
            existing_client_id = self._agent_type_to_client_id[register_agent_type.type]
            logger.warning(
                f"Agent type {register_agent_type.type} already registered with client {existing_client_id}, overwriting the client mapping to client {client_id}."
            )
        self._agent_type_to_client_id[register_agent_type.type] = client_id
