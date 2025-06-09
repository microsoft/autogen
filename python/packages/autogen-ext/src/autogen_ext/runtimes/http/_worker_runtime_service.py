from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set
import uuid

from autogen_core import Subscription, TopicId
from autogen_core import SubscriptionManager
from fastapi import WebSocket

logger = logging.getLogger("autogen_core")


class HttpAgentService:
    """
    A "servicer" that keeps track of:
      - client_id -> websockets (for streaming messages)
      - agent_type -> client_id
      - subscription manager
    and provides methods to handle inbound requests from your FastAPI routes.
    """

    def __init__(self) -> None:
        self._subscription_manager = SubscriptionManager()
        self._agent_type_to_client_id: Dict[str, str] = {}
        self._client_id_to_ws: Dict[str, WebSocket] = {}
        self._client_id_to_sub_ids: Dict[str, Set[str]] = {}
        self._pending: Dict[str, Dict[str, asyncio.Future]] = {}

    async def on_client_connected(self, client_id: str, ws: WebSocket) -> None:
        self._client_id_to_ws[client_id] = ws
        logger.info(f"Client {client_id} connected")

    async def on_client_disconnected(self, client_id: str) -> None:
        if client_id in self._client_id_to_ws:
            del self._client_id_to_ws[client_id]
        # remove from agent_type map
        to_delete = []
        for atype, cid in self._agent_type_to_client_id.items():
            if cid == client_id:
                to_delete.append(atype)
        for td in to_delete:
            del self._agent_type_to_client_id[td]

        # remove subscriptions
        if client_id in self._client_id_to_sub_ids:
            for sub_id in self._client_id_to_sub_ids[client_id]:
                try:
                    await self._subscription_manager.remove_subscription(sub_id)
                except ValueError:
                    pass
            del self._client_id_to_sub_ids[client_id]

        logger.info(f"Client {client_id} disconnected")

    async def handle_websocket_message(self, client_id: str, data: dict) -> None:
        """
        Called by your FastAPI WebSocket route each time a message arrives.
        We route it (like the gRPC servicer) to the proper place:
          - 'type': 'request' -> forward to the correct agent client
          - 'type': 'cloud_event' -> publish
          - 'type': 'response' -> fulfill a pending future, etc.
        But in this HTTP sample host, we assume we are the "router" for multiple worker-clients,
        so we dispatch from one client to another or to local logic, the same as gRPC version does.
        """

        msg_type = data.get("type")

        if msg_type == "request":
            await self._process_request(client_id, data)
        elif msg_type == "response":
            await self._process_response(client_id, data)
        elif msg_type == "cloud_event":
            await self._process_cloud_event(client_id, data)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def register_agent_type(self, client_id: str, agent_type: str) -> None:
        if agent_type in self._agent_type_to_client_id:
            raise ValueError(f"Agent type {agent_type} already registered.")
        self._agent_type_to_client_id[agent_type] = client_id
        logger.info(f"Registered agent type '{agent_type}' -> client {client_id}")

    async def add_subscription(self, client_id: str, sub: Subscription) -> None:
        await self._subscription_manager.add_subscription(sub)
        self._client_id_to_sub_ids.setdefault(client_id, set()).add(sub.id)

    async def remove_subscription(self, client_id: str, sub_id: str) -> None:
        await self._subscription_manager.remove_subscription(sub_id)
        if client_id in self._client_id_to_sub_ids:
            self._client_id_to_sub_ids[client_id].discard(sub_id)

    async def get_subscriptions(self) -> list[Subscription]:
        return list(self._subscription_manager.subscriptions)

    async def rpc_agent_call(self, sender_cid: str, **params):
        target = params["target"]
        agent_type = target["type"]
        request_id = params.get("id", str(uuid.uuid4()))

        logger.info(f"RPC agent call from {sender_cid} to agent_type={agent_type}, request_id={request_id}")

        if agent_type not in self._agent_type_to_client_id:
            logger.error(f"Agent type {agent_type} not registered")
            raise ValueError(f"agent type {agent_type} not registered")

        tgt_cid = self._agent_type_to_client_id[agent_type]
        ws = self._client_id_to_ws.get(tgt_cid)
        if ws is None:
            logger.error(f"Target client {tgt_cid} not connected")
            raise ValueError(f"target client {tgt_cid} not connected")

        # forward, await response
        forward = {
            "type": "request",
            "request_id": request_id,
            **params,
            "original_sender": sender_cid,
        }
        logger.info(f"Creating future for request_id={request_id}")
        fut = asyncio.get_running_loop().create_future()
        self._pending.setdefault(tgt_cid, {})[request_id] = fut

        try:
            logger.info(f"Sending request to target {tgt_cid}")
            await ws.send_json(forward)

            # Wait for response with a timeout to prevent hanging
            try:
                logger.info(f"Waiting for response to request_id={request_id}")
                reply = await asyncio.wait_for(fut, timeout=20.0)  # 20 second timeout
                logger.info(f"Received response for request_id={request_id}")
                return reply  # returned to caller as JSON‑RPC result
            except asyncio.TimeoutError:
                # Clean up the pending future
                if tgt_cid in self._pending and request_id in self._pending[tgt_cid]:
                    del self._pending[tgt_cid][request_id]
                logger.error(f"Timeout waiting for response to request_id={request_id}")
                raise ValueError(f"Timeout waiting for response from agent {agent_type}")
        except Exception as e:
            logger.error(f"Error in rpc_agent_call: {str(e)}")
            # Clean up the pending future
            if tgt_cid in self._pending and request_id in self._pending[tgt_cid]:
                del self._pending[tgt_cid][request_id]
            raise

    async def rpc_agent_publish(self, sender_cid: str, **payload):
        # Re‑use existing _process_cloud_event
        await self._process_cloud_event(sender_cid, {"type": "cloud_event", **payload})

    # ----------------------------------------------------------------
    # Internals to route requests among multiple clients
    # ----------------------------------------------------------------
    async def _process_request(self, client_id: str, data: dict) -> None:
        """
        The worker is sending a 'request' to the host. This host logic
        finds the 'target' agent's client and forwards the request there.
        Then it must also track a future to receive the response from that client
        and send it back to 'client_id'.
        """
        request_id = data.get("request_id")
        target = data.get("target", {})
        agent_type = target.get("type")

        logger.info(f"Processing request from {client_id} to agent_type={agent_type}, request_id={request_id}")

        # find the client that registered that agent type
        if agent_type not in self._agent_type_to_client_id:
            logger.error(f"Agent type {agent_type} not found for request {request_id}")
            # Return error?
            await self._send_channel_message(
                client_id,
                {
                    "type": "response",
                    "request_id": request_id,
                    "error": f"Agent type {agent_type} not found",
                },
            )
            return
        target_client_id = self._agent_type_to_client_id[agent_type]
        logger.info(f"Found target client {target_client_id} for agent_type={agent_type}")

        # forward this request over the WebSocket to the target_client_id
        # but we also need a future to capture the response from the target
        forward_ws = self._client_id_to_ws.get(target_client_id)
        if not forward_ws:
            logger.error(f"Target client {target_client_id} not connected for request {request_id}")
            await self._send_channel_message(
                client_id,
                {
                    "type": "response",
                    "request_id": request_id,
                    "error": f"Client for agent {agent_type} not found or not connected",
                },
            )
            return

        # For multi-step: we store some "pending" structure (like gRPC did),
        # but for brevity, let's define a simpler approach or skip the details.
        # We'll attach the 'original_sender' so we know whom to respond to.
        data["original_sender"] = client_id

        logger.info(f"Forwarding request {request_id} to target client {target_client_id}")
        await forward_ws.send_json(data)
        logger.info(f"Successfully forwarded request {request_id}")

    async def _process_response(self, client_id: str, data: dict) -> None:
        """
        The worker is sending a 'response' to the host after handling some request.
        We see who the original sender was and forward them the 'response'.
        """
        request_id = data.get("request_id")
        logger.info(f"Processing response from {client_id} for request_id={request_id}")

        original_sender = data.get("original_sender")
        if not original_sender:
            # This means we are missing info. Possibly a logic error in this example.
            logger.error(f"Response with no original_sender. Cannot route back. Request ID: {request_id}")
            return

        # We need to complete the pending future as well
        if client_id in self._pending and request_id in self._pending[client_id]:
            logger.info(f"Setting result for future with request_id={request_id}")
            future = self._pending[client_id][request_id]

            if "error" in data and data["error"]:
                logger.error(f"Response contains error: {data['error']}")
                future.set_exception(RuntimeError(data["error"]))
            else:
                future.set_result(data)

            # Remove the future from pending
            del self._pending[client_id][request_id]
        else:
            logger.warning(f"No pending future found for client={client_id}, request_id={request_id}")

        # Forward to the original_sender
        ws = self._client_id_to_ws.get(original_sender)
        if ws:
            # remove the 'original_sender' field
            data.pop("original_sender", None)
            logger.info(f"Forwarding response to original sender {original_sender}")
            await ws.send_json(data)
        else:
            logger.error(f"Cannot forward response - original sender {original_sender} not connected")

    async def _process_cloud_event(self, client_id: str, data: dict) -> None:
        """
        The worker is publishing an event. We find all matching subscriptions and forward
        to the relevant worker(s).
        """
        topic_info = data.get("topic", {})
        topic_id = TopicId(topic_info.get("type", ""), topic_info.get("source", ""))
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)
        # For each recipient, find that agent_type -> find the client_id -> send
        for agent_id in recipients:
            # skip if agent_id is the same as the publisher
            if agent_id.type not in self._agent_type_to_client_id:
                continue
            target_cid = self._agent_type_to_client_id[agent_id.type]
            if target_cid == client_id:
                continue
            ws = self._client_id_to_ws.get(target_cid)
            if ws:
                await ws.send_json(data)

    async def _send_channel_message(self, client_id: str, msg: dict) -> None:
        ws = self._client_id_to_ws.get(client_id)
        if ws:
            await ws.send_json(msg)
        else:
            logger.error(f"Cannot send message to client {client_id}; no active socket.")
