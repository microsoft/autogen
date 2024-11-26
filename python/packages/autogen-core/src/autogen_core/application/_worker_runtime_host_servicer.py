import asyncio
import logging
from _collections_abc import AsyncIterator, Iterator
from asyncio import Future, Task
from typing import Any, Dict, Set

from autogen_core.components._type_prefix_subscription import TypePrefixSubscription

from ..base import Subscription, TopicId
from ..components import TypeSubscription
from ._helpers import SubscriptionManager
from ._utils import GRPC_IMPORT_ERROR_STR

try:
    import grpc
except ImportError as e:
    raise ImportError(GRPC_IMPORT_ERROR_STR) from e

from .protos import agent_worker_pb2, agent_worker_pb2_grpc

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")


class WorkerAgentRuntimeHostServicer(agent_worker_pb2_grpc.AgentRpcServicer):
    """A gRPC servicer that hosts message delivery service for agents."""

    def __init__(self) -> None:
        self._client_id = 0
        self._client_id_lock = asyncio.Lock()
        self._send_queues: Dict[int, asyncio.Queue[agent_worker_pb2.Message]] = {}
        self._agent_type_to_client_id_lock = asyncio.Lock()
        self._agent_type_to_client_id: Dict[str, int] = {}
        self._pending_responses: Dict[int, Dict[str, Future[Any]]] = {}
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._client_id_to_subscription_id_mapping: Dict[int, set[str]] = {}

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
                logger.info(f"Sent message to client {client_id}: {message}")
            # Wait for the receiving task to finish.
            await receiving_task

        finally:
            # Clean up the client connection.
            del self._send_queues[client_id]
            # Cancel pending requests sent to this client.
            for future in self._pending_responses.pop(client_id, {}).values():
                future.cancel()
            # Remove the client id from the agent type to client id mapping.
            await self._on_client_disconnect(client_id)

    async def _on_client_disconnect(self, client_id: int) -> None:
        async with self._agent_type_to_client_id_lock:
            agent_types = [agent_type for agent_type, id_ in self._agent_type_to_client_id.items() if id_ == client_id]
            for agent_type in agent_types:
                logger.info(f"Removing agent type {agent_type} from agent type to client id mapping")
                del self._agent_type_to_client_id[agent_type]
            for sub_id in self._client_id_to_subscription_id_mapping.get(client_id, []):
                logger.info(f"Client id {client_id} disconnected. Removing corresponding subscription with id {id}")
                await self._subscription_manager.remove_subscription(sub_id)
        logger.info(f"Client {client_id} disconnected successfully")

    def _raise_on_exception(self, task: Task[Any]) -> None:
        exception = task.exception()
        if exception is not None:
            raise exception

    async def _receive_messages(
        self, client_id: int, request_iterator: AsyncIterator[agent_worker_pb2.Message]
    ) -> None:
        # Receive messages from the client and process them.
        async for message in request_iterator:
            logger.info(f"Received message from client {client_id}: {message}")
            oneofcase = message.WhichOneof("message")
            match oneofcase:
                case "request":
                    request: agent_worker_pb2.RpcRequest = message.request
                    task = asyncio.create_task(self._process_request(request, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._raise_on_exception)
                    task.add_done_callback(self._background_tasks.discard)
                case "response":
                    response: agent_worker_pb2.RpcResponse = message.response
                    task = asyncio.create_task(self._process_response(response, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._raise_on_exception)
                    task.add_done_callback(self._background_tasks.discard)
                case "event":
                    event: agent_worker_pb2.Event = message.event
                    task = asyncio.create_task(self._process_event(event))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._raise_on_exception)
                    task.add_done_callback(self._background_tasks.discard)
                case "registerAgentTypeRequest":
                    register_agent_type: agent_worker_pb2.RegisterAgentTypeRequest = message.registerAgentTypeRequest
                    task = asyncio.create_task(
                        self._process_register_agent_type_request(register_agent_type, client_id)
                    )
                    self._background_tasks.add(task)
                    task.add_done_callback(self._raise_on_exception)
                    task.add_done_callback(self._background_tasks.discard)
                case "addSubscriptionRequest":
                    add_subscription: agent_worker_pb2.AddSubscriptionRequest = message.addSubscriptionRequest
                    task = asyncio.create_task(self._process_add_subscription_request(add_subscription, client_id))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._raise_on_exception)
                    task.add_done_callback(self._background_tasks.discard)
                case "registerAgentTypeResponse" | "addSubscriptionResponse":
                    logger.warning(f"Received unexpected message type: {oneofcase}")
                case None:
                    logger.warning("Received empty message")
                case other:
                    logger.error(f"Received unexpected message: {other}")

    async def _process_request(self, request: agent_worker_pb2.RpcRequest, client_id: int) -> None:
        # Deliver the message to a client given the target agent type.
        async with self._agent_type_to_client_id_lock:
            target_client_id = self._agent_type_to_client_id.get(request.target.type)
        if target_client_id is None:
            logger.error(f"Agent {request.target.type} not found, failed to deliver message.")
            return
        target_send_queue = self._send_queues.get(target_client_id)
        if target_send_queue is None:
            logger.error(f"Client {target_client_id} not found, failed to deliver message.")
            return
        await target_send_queue.put(agent_worker_pb2.Message(request=request))

        # Create a future to wait for the response from the target.
        future = asyncio.get_event_loop().create_future()
        self._pending_responses.setdefault(target_client_id, {})[request.request_id] = future

        # Create a task to wait for the response and send it back to the client.
        send_response_task = asyncio.create_task(self._wait_and_send_response(future, client_id))
        self._background_tasks.add(send_response_task)
        send_response_task.add_done_callback(self._raise_on_exception)
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
        future = self._pending_responses[client_id].pop(response.request_id)
        future.set_result(response)

    async def _process_event(self, event: agent_worker_pb2.Event) -> None:
        topic_id = TopicId(type=event.topic_type, source=event.topic_source)
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)
        # Get the client ids of the recipients.
        async with self._agent_type_to_client_id_lock:
            client_ids: Set[int] = set()
            for recipient in recipients:
                client_id = self._agent_type_to_client_id.get(recipient.type)
                if client_id is not None:
                    client_ids.add(client_id)
                else:
                    logger.error(f"Agent {recipient.type} and its client not found for topic {topic_id}.")
        # Deliver the event to clients.
        for client_id in client_ids:
            await self._send_queues[client_id].put(agent_worker_pb2.Message(event=event))

    async def _process_register_agent_type_request(
        self, register_agent_type_req: agent_worker_pb2.RegisterAgentTypeRequest, client_id: int
    ) -> None:
        # Register the agent type with the host runtime.
        async with self._agent_type_to_client_id_lock:
            if register_agent_type_req.type in self._agent_type_to_client_id:
                existing_client_id = self._agent_type_to_client_id[register_agent_type_req.type]
                logger.error(
                    f"Agent type {register_agent_type_req.type} already registered with client {existing_client_id}."
                )
                success = False
                error = f"Agent type {register_agent_type_req.type} already registered."
            else:
                self._agent_type_to_client_id[register_agent_type_req.type] = client_id
                success = True
                error = None
        # Send a response back to the client.
        await self._send_queues[client_id].put(
            agent_worker_pb2.Message(
                registerAgentTypeResponse=agent_worker_pb2.RegisterAgentTypeResponse(
                    request_id=register_agent_type_req.request_id, success=success, error=error
                )
            )
        )

    async def _process_add_subscription_request(
        self, add_subscription_req: agent_worker_pb2.AddSubscriptionRequest, client_id: int
    ) -> None:
        oneofcase = add_subscription_req.subscription.WhichOneof("subscription")
        subscription: Subscription | None = None
        match oneofcase:
            case "typeSubscription":
                type_subscription_msg: agent_worker_pb2.TypeSubscription = (
                    add_subscription_req.subscription.typeSubscription
                )
                subscription = TypeSubscription(
                    topic_type=type_subscription_msg.topic_type, agent_type=type_subscription_msg.agent_type
                )

            case "typePrefixSubscription":
                type_prefix_subscription_msg: agent_worker_pb2.TypePrefixSubscription = (
                    add_subscription_req.subscription.typePrefixSubscription
                )
                subscription = TypePrefixSubscription(
                    topic_type_prefix=type_prefix_subscription_msg.topic_type_prefix,
                    agent_type=type_prefix_subscription_msg.agent_type,
                )
            case None:
                logger.warning("Received empty subscription message")

        if subscription is not None:
            try:
                await self._subscription_manager.add_subscription(subscription)
                subscription_ids = self._client_id_to_subscription_id_mapping.setdefault(client_id, set())
                subscription_ids.add(subscription.id)
                success = True
                error = None
            except ValueError as e:
                success = False
                error = str(e)
            # Send a response back to the client.
            await self._send_queues[client_id].put(
                agent_worker_pb2.Message(
                    addSubscriptionResponse=agent_worker_pb2.AddSubscriptionResponse(
                        request_id=add_subscription_req.request_id, success=success, error=error
                    )
                )
            )

    async def GetState(  # type: ignore
        self,
        request: agent_worker_pb2.AgentId,
        context: grpc.aio.ServicerContext[agent_worker_pb2.AgentId, agent_worker_pb2.GetStateResponse],
    ) -> agent_worker_pb2.GetStateResponse:  # type: ignore
        raise NotImplementedError("Method not implemented!")

    async def SaveState(  # type: ignore
        self,
        request: agent_worker_pb2.AgentState,
        context: grpc.aio.ServicerContext[agent_worker_pb2.AgentId, agent_worker_pb2.SaveStateResponse],
    ) -> agent_worker_pb2.SaveStateResponse:  # type: ignore
        raise NotImplementedError("Method not implemented!")
