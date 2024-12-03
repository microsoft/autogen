from __future__ import annotations

from typing import Optional


def format_rpc_request_topic(rpc_recipient_agent_type: str, rpc_sender_agent_type: str) -> str:
    return f"{rpc_recipient_agent_type}:rpc_request={rpc_sender_agent_type}"


def format_rpc_response_topic(rpc_sender_agent_type: str, request_id: str) -> str:
    return f"{rpc_sender_agent_type}:rpc_response={request_id}"


# If is an rpc response, return the request id
def is_rpc_response(topic_type: str) -> Optional[str]:
    topic_segments = topic_type.split(":")
    # Find if there is a segment starting with :rpc_response=
    for segment in topic_segments:
        if segment.startswith("rpc_response="):
            return segment[len("rpc_response=") :]
    return None


# If is an rpc response, return the requestor agent type
def is_rpc_request(topic_type: str) -> Optional[str]:
    topic_segments = topic_type.split(":")
    # Find if there is a segment starting with :rpc_request=
    for segment in topic_segments:
        if segment.startswith("rpc_request="):
            return segment[len("rpc_request=") :]
    return None
