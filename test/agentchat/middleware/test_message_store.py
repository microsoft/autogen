from typing import Any, Dict, Optional, Union

import pytest

from autogen.agentchat.agent import Agent
from autogen.agentchat.middleware.message_store import MessageStoreMiddleware


def _dummy_reply(
    message: Union[Dict[str, Any], str],
    sender: Agent,
    request_reply: Optional[bool] = None,
    silent: Optional[bool] = False,
) -> Union[str, Dict[str, str]]:
    """Generate a dummy reply."""
    if isinstance(message, str):
        return "Hello World"
    else:
        return {"content": "Hello World", "role": "assistant"}


async def _dummy_reply_async(
    message: Union[Dict[str, Any], str],
    sender: Agent,
    request_reply: Optional[bool] = None,
    silent: Optional[bool] = False,
) -> Union[str, Dict[str, str]]:
    """Generate a dummy reply."""
    return _dummy_reply(message, sender, request_reply, silent)


def test_message_store() -> None:
    md = MessageStoreMiddleware(name="Assistant")
    message = {"role": "user", "content": "Hi there"}
    sender = Agent("User")
    reply = md.call(
        message=message,
        sender=sender,
        request_reply=True,
        silent=False,
        next=_dummy_reply,
    )
    assert reply == {"content": "Hello World", "role": "assistant"}
    assert md.oai_messages[sender] == [
        {"content": "Hi there", "role": "user"},
        {"content": "Hello World", "role": "assistant"},
    ]


@pytest.mark.asyncio()
async def test_message_store_async() -> None:
    md = MessageStoreMiddleware(name="Assistant")
    message = {"role": "user", "content": "Hi there"}
    sender = Agent("User")
    reply = await md.a_call(
        message=message,
        sender=sender,
        request_reply=True,
        silent=False,
        next=_dummy_reply_async,
    )
    assert reply == {"content": "Hello World", "role": "assistant"}
    assert md.oai_messages[sender] == [
        {"content": "Hi there", "role": "user"},
        {"content": "Hello World", "role": "assistant"},
    ]
