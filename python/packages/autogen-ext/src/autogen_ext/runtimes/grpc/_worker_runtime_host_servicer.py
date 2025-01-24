import asyncio
import logging
from _collections_abc import AsyncIterator
from asyncio import Future, Task
from typing import Any, Dict, Sequence, Set, Tuple

from autogen_core import TopicId
from autogen_core._runtime_impl_helpers import SubscriptionManager

from ._constants import GRPC_IMPORT_ERROR_STR
from ._utils import subscription_from_proto

try:
    import grpc
except ImportError as e:
    raise ImportError(GRPC_IMPORT_ERROR_STR) from e

from .protos import agent_worker_pb2, agent_worker_pb2_grpc, cloudevent_pb2

logger = logging.getLogger("autogen_core")
event_logger = logging.getLogger("autogen_core.events")

ClientConnectionId = str


def metadata_to_dict(metadata: Sequence[Tuple[str, str]] | None) -> Dict[str, str]:
    if metadata is None:
        return {}
    return {key: value for key, value in metadata}


async def get_client_id_or_abort(context: grpc.aio.ServicerContext[Any, Any]) -> str:  # type: ignore
    # The type hint on context.invocation_metadata() is incorrect.
    metadata = metadata_to_dict(context.invocation_metadata())  # type: ignore
    if (client_id := metadata.get("client-id")) is None:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "client-id metadata not found.")

    return client_id  # type: ignore


class GrpcWorkerAgentRuntimeHostServicer(agent_worker_pb2_grpc.AgentRpcServicer):
    """A gRPC servicer that hosts message delivery service for agents."""

    def __init__(self) -> None:
        self._send_queues: Dict[ClientConnectionId, asyncio.Queue[agent_worker_pb2.Message]] = {}
        self._agent_type_to_client_id_lock = asyncio.Lock()
        self._agent_type_to_client_id: Dict[str, ClientConnectionId] = {}
        self._pending_responses: Dict[ClientConnectionId, Dict[str, Future[Any]]] = {}
        self._background_tasks: Set[Task[Any]] = set()
        self._subscription_manager = SubscriptionManager()
        self._client_id_to_subscription_id_mapping: Dict[ClientConnectionId, set[str]] = {}

    async def OpenChannel(  # type: ignore
        self,
        request_iterator: AsyncIterator[agent_worker_pb2.Message],
        context: grpc.aio.ServicerContext[agent_worker_pb2.Message, agent_worker_pb2.Message],
    ) -> AsyncIterator[agent_worker_pb2.Message]:
        client_id = await get_client_id_or_abort(context)

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

    async def _on_client_disconnect(self, client_id: ClientConnectionId) -> None:
        async with self._agent_type_to_client_id_lock:
            agent_types = [agent_type for agent_type, id_ in self._agent_type_to_client_id.items() if id_ == client_id]
            for agent_type in agent_types:
                logger.info(f"Removing agent type {agent_type} from agent type to client id mapping")
                del self._agent_type_to_client_id[agent_type]
            for sub_id in self._client_id_to_subscription_id_mapping.get(client_id, set()):
                logger.info(f"Client id {client_id} disconnected. Removing corresponding subscription with id {id}")
                await self._subscription_manager.remove_subscription(sub_id)
        logger.info(f"Client {client_id} disconnected successfully")

    def _raise_on_exception(self, task: Task[Any]) -> None:
        exception = task.exception()
        if exception is not None:
            raise exception

    async def _receive_messages(
        self, client_id: ClientConnectionId, request_iterator: AsyncIterator[agent_worker_pb2.Message]
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
                case "cloudEvent":
                    task = asyncio.create_task(self._process_event(message.cloudEvent))
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

    async def _process_request(self, request: agent_worker_pb2.RpcRequest, client_id: ClientConnectionId) -> None:
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

    async def _wait_and_send_response(
        self, future: Future[agent_worker_pb2.RpcResponse], client_id: ClientConnectionId
    ) -> None:
        response = await future
        message = agent_worker_pb2.Message(response=response)
        send_queue = self._send_queues.get(client_id)
        if send_queue is None:
            logger.error(f"Client {client_id} not found, failed to send response message.")
            return
        await send_queue.put(message)

    async def _process_response(self, response: agent_worker_pb2.RpcResponse, client_id: ClientConnectionId) -> None:
        # Setting the result of the future will send the response back to the original sender.
        future = self._pending_responses[client_id].pop(response.request_id)
        future.set_result(response)

    async def _process_event(self, event: cloudevent_pb2.CloudEvent) -> None:
        topic_id = TopicId(type=event.type, source=event.source)
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)
        # Get the client ids of the recipients.
        async with self._agent_type_to_client_id_lock:
            client_ids: Set[ClientConnectionId] = set()
            for recipient in recipients:
                client_id = self._agent_type_to_client_id.get(recipient.type)
                if client_id is not None:
                    client_ids.add(client_id)
                else:
                    logger.error(f"Agent {recipient.type} and its client not found for topic {topic_id}.")
        # Deliver the event to clients.
        for client_id in client_ids:
            await self._send_queues[client_id].put(agent_worker_pb2.Message(cloudEvent=event))

    async def _process_register_agent_type_request(
        self, register_agent_type_req: agent_worker_pb2.RegisterAgentTypeRequest, client_id: ClientConnectionId
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
        self, add_subscription_req: agent_worker_pb2.AddSubscriptionRequest, client_id: ClientConnectionId
    ) -> None:
        subscription = subscription_from_proto(add_subscription_req.subscription)
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

    async def RegisterAgent(  # type: ignore
        self,
        request: agent_worker_pb2.RegisterAgentTypeRequest,
        context: grpc.aio.ServicerContext[
            agent_worker_pb2.RegisterAgentTypeRequest, agent_worker_pb2.RegisterAgentTypeResponse
        ],
    ) -> agent_worker_pb2.RegisterAgentTypeResponse:
        client_id = await get_client_id_or_abort(context)

        async with self._agent_type_to_client_id_lock:
            if request.type in self._agent_type_to_client_id:
                existing_client_id = self._agent_type_to_client_id[request.type]
                logger.error(f"Agent type {request.type} already registered with client {existing_client_id}.")
                success = False
                error = f"Agent type {request.type} already registered."
            else:
                self._agent_type_to_client_id[request.type] = client_id
                success = True
                error = None
        return agent_worker_pb2.RegisterAgentTypeResponse(request_id=request.request_id, success=success, error=error)

    async def AddSubscription(  # type: ignore
        self,
        request: agent_worker_pb2.AddSubscriptionRequest,
        context: grpc.aio.ServicerContext[
            agent_worker_pb2.AddSubscriptionRequest, agent_worker_pb2.AddSubscriptionResponse
        ],
    ) -> agent_worker_pb2.AddSubscriptionResponse:
        client_id = await get_client_id_or_abort(context)

        subscription = subscription_from_proto(request.subscription)
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
        return agent_worker_pb2.AddSubscriptionResponse(request_id=request.request_id, success=success, error=error)

    async def RemoveSubscription(  # type: ignore
        self,
        request: agent_worker_pb2.RemoveSubscriptionRequest,
        context: grpc.aio.ServicerContext[
            agent_worker_pb2.RemoveSubscriptionRequest, agent_worker_pb2.RemoveSubscriptionResponse
        ],
    ) -> agent_worker_pb2.RemoveSubscriptionResponse:
        _client_id = await get_client_id_or_abort(context)
        raise NotImplementedError("Method not implemented.")

    async def GetSubscriptions(  # type: ignore
        self,
        request: agent_worker_pb2.GetSubscriptionsRequest,
        context: grpc.aio.ServicerContext[
            agent_worker_pb2.GetSubscriptionsRequest, agent_worker_pb2.GetSubscriptionsResponse
        ],
    ) -> agent_worker_pb2.GetSubscriptionsResponse:
        _client_id = await get_client_id_or_abort(context)
        raise NotImplementedError("Method not implemented.")

    async def GetState(  # type: ignore
        self,
        request: agent_worker_pb2.AgentId,
        context: grpc.aio.ServicerContext[agent_worker_pb2.AgentId, agent_worker_pb2.GetStateResponse],
    ) -> agent_worker_pb2.GetStateResponse:
        raise NotImplementedError("Method not implemented!")

    async def SaveState(  # type: ignore
        self,
        request: agent_worker_pb2.AgentState,
        context: grpc.aio.ServicerContext[agent_worker_pb2.AgentId, agent_worker_pb2.SaveStateResponse],
    ) -> agent_worker_pb2.SaveStateResponse:
        raise NotImplementedError("Method not implemented!")
