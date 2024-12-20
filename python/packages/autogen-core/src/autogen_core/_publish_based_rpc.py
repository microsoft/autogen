import asyncio
import uuid
import warnings
from typing import Any

from autogen_core._types import CancelledRpc, CancelRpc, CantHandleMessageResponse, RpcMessageDroppedResponse
from autogen_core.exceptions import CantHandleException, MessageDroppedException

from ._agent_id import AgentId
from ._agent_runtime import AgentRuntime
from ._cancellation_token import CancellationToken
from ._closure_agent import ClosureAgent, ClosureContext
from ._message_context import MessageContext
from ._topic import TopicId
from ._well_known_topics import (
    format_error_topic,
    format_rpc_cancel_topic,
    format_rpc_request_topic,
    format_rpc_response_topic,
)


class PublishBasedRpcMixin(AgentRuntime):
    async def send_message(
        self: AgentRuntime,
        message: Any,
        recipient: AgentId,
        *,
        cancellation_token: CancellationToken | None = None,
        timeout: float | None = None,
    ) -> Any:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        rpc_request_id = str(uuid.uuid4())
        # TODO add "-" to topic and agent type allowed characters in spec
        closure_agent_type = f"rpc_receiver_{recipient.type}_{rpc_request_id}"

        future: asyncio.Future[Any] = asyncio.Future()
        expected_response_topic_type = format_rpc_response_topic(
            rpc_sender_agent_type=closure_agent_type, request_id=rpc_request_id
        )
        expected_error_topic_type = format_error_topic(closure_agent_type, request_id=rpc_request_id)

        async def set_result(closure_context: ClosureContext, message: Any, ctx: MessageContext) -> None:
            assert ctx.topic_id is not None
            if ctx.topic_id.type == expected_response_topic_type:
                if isinstance(message, CancelledRpc):
                    future.cancel()
                else:
                    future.set_result(message)
            elif ctx.topic_id.type == expected_error_topic_type:
                # Well known things we handle - dropped message, cant handle
                # If the message is for a dropped message
                if isinstance(message, CantHandleMessageResponse):
                    future.set_exception(CantHandleException())
                if isinstance(message, RpcMessageDroppedResponse):
                    future.set_exception(MessageDroppedException())
                else:
                    warnings.warn(
                        f"{closure_agent_type} received an unexpected message on topic type {ctx.topic_id.type}.",
                        stacklevel=2,
                    )
            else:
                warnings.warn(
                    f"{closure_agent_type} received an unexpected message on topic type {ctx.topic_id.type}. Expected {expected_response_topic_type}",
                    stacklevel=2,
                )

            # TODO: remove agent after response is received

        await ClosureAgent.register_closure(
            runtime=self,
            type=closure_agent_type,
            closure=set_result,
            forward_unbound_rpc_responses_to_handler=True,
        )

        rpc_request_topic_id = format_rpc_request_topic(
            rpc_recipient_agent_type=recipient.type, rpc_sender_agent_type=closure_agent_type
        )
        await self.publish_message(
            message=message,
            topic_id=TopicId(type=rpc_request_topic_id, source=recipient.key),
            message_id=rpc_request_id,
            sender=AgentId(type=closure_agent_type, key=recipient.key),
        )

        async def send_cancel():
            cancel_topic = format_rpc_cancel_topic(rpc_recipient_agent_type=recipient.type, request_id=rpc_request_id)
            await self.publish_message(
                message=CancelRpc(),
                topic_id=TopicId(cancel_topic, recipient.key),
            )

        cancellation_token.add_callback(send_cancel)

        async with asyncio.timeout(timeout):
            return await future

        # register a closure agent...
