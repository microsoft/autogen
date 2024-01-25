from typing import Any, Dict, Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from autogen.agentchat.agent import Agent
from autogen.agentchat.middleware.termination import TerminationAndHumanReplyMiddleware


def _dummpy_reply(
    message: Union[Dict[str, Any], str],
    sender: Agent,
    silent: Optional[bool] = False,
) -> Union[str, Dict[str, str]]:
    """Generate a dummy reply."""
    if isinstance(message, str):
        return "Hello World"
    else:
        return {"content": "Hello World", "role": "assistant"}


async def _dummpy_reply_async(
    message: Union[Dict[str, Any], str],
    sender: Agent,
    silent: Optional[bool] = False,
) -> Union[str, Dict[str, str]]:
    """Generate a dummy reply."""
    return _dummpy_reply(message, sender, silent)


def test_termination_termination_msg() -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="NEVER")
    sender = Agent("User")
    reply = md.call(messages=[{"role": "user", "content": "TERMINATE"}], sender=sender)
    assert reply is None

    # Test custom termination message.
    md = TerminationAndHumanReplyMiddleware(
        human_input_mode="NEVER", is_termination_msg=lambda x: x["content"] == "BYE"
    )
    sender = Agent("User")
    reply = md.call(messages=[{"role": "user", "content": "BYE"}], sender=sender)
    assert reply is None


@pytest.mark.asyncio()
async def test_termination_termination_msg_async() -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="NEVER")
    sender = Agent("User")
    reply = await md.a_call(messages=[{"role": "user", "content": "TERMINATE"}], sender=sender)
    assert reply is None

    # Test custom termination message.
    md = TerminationAndHumanReplyMiddleware(
        human_input_mode="NEVER", is_termination_msg=lambda x: x["content"] == "BYE"
    )
    sender = Agent("User")
    reply = await md.a_call(messages=[{"role": "user", "content": "BYE"}], sender=sender)
    assert reply is None


@patch(
    "autogen.agentchat.middleware.termination.TerminationAndHumanReplyMiddleware._get_human_input",
    return_value="I am a human.",
)
def test_human_input(mock_human_input: MagicMock) -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="ALWAYS")
    sender = Agent("User")
    reply = md.call(messages=[{"role": "user", "content": "Hey"}], sender=sender, next=_dummpy_reply)
    mock_human_input.assert_called_once()
    assert reply == {"content": "I am a human.", "role": "user"}


@pytest.mark.asyncio()
@patch(
    "autogen.agentchat.middleware.termination.TerminationAndHumanReplyMiddleware._a_get_human_input",
    return_value="I am a human.",
)
async def test_human_input_async(mock_human_input: MagicMock) -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="ALWAYS")
    sender = Agent("User")
    reply = await md.a_call(messages=[{"role": "user", "content": "Hey"}], sender=sender, next=_dummpy_reply_async)
    mock_human_input.assert_called_once()
    assert reply == {"content": "I am a human.", "role": "user"}


@patch(
    "autogen.agentchat.middleware.termination.TerminationAndHumanReplyMiddleware._get_human_input",
    return_value="I am a human.",
)
def test_human_input_termination(mock_human_input: MagicMock) -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="TERIMATION")
    sender = Agent("User")
    reply = md.call(messages=[{"role": "user", "content": "TERMINATE"}], sender=sender, next=_dummpy_reply)
    mock_human_input.assert_called_once()
    assert reply == {"content": "I am a human.", "role": "user"}


@pytest.mark.asyncio()
@patch(
    "autogen.agentchat.middleware.termination.TerminationAndHumanReplyMiddleware._a_get_human_input",
    return_value="I am a human.",
)
async def test_human_input_termination_async(mock_human_input: MagicMock) -> None:
    # Test default termination message.
    md = TerminationAndHumanReplyMiddleware(human_input_mode="TERIMATION")
    sender = Agent("User")
    reply = await md.a_call(
        messages=[{"role": "user", "content": "TERMINATE"}], sender=sender, next=_dummpy_reply_async
    )
    mock_human_input.assert_called_once()
    assert reply == {"content": "I am a human.", "role": "user"}
