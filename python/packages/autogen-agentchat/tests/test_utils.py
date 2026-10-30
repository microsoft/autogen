from typing import List

import pytest
from autogen_agentchat.utils import ensure_alternating_roles, remove_images
from autogen_core import Image
from autogen_core.models import AssistantMessage, LLMMessage, SystemMessage, UserMessage


@pytest.mark.asyncio
async def test_remove_images() -> None:
    img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
    messages: List[LLMMessage] = [
        SystemMessage(content="System.1"),
        UserMessage(content=["User.1", Image.from_base64(img_base64)], source="user.1"),
        AssistantMessage(content="Assistant.1", source="assistant.1"),
        UserMessage(content="User.2", source="assistant.2"),
    ]

    result = remove_images(messages)

    # Check all the invariants
    assert len(result) == 4
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], UserMessage)
    assert isinstance(result[2], AssistantMessage)
    assert isinstance(result[3], UserMessage)
    assert result[0].content == messages[0].content
    assert result[2].content == messages[2].content
    assert result[3].content == messages[3].content
    assert isinstance(messages[2], AssistantMessage)
    assert isinstance(messages[3], UserMessage)
    assert result[2].source == messages[2].source
    assert result[3].source == messages[3].source

    # Check that the image was removed.
    assert result[1].content == "User.1\n<image>"


# ---------------------------------------------------------------------------
# Tests for ensure_alternating_roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_alternating_roles_already_alternating() -> None:
    """Already-alternating messages must be returned unchanged."""
    messages: List[LLMMessage] = [
        UserMessage(content="User.1", source="user"),
        AssistantMessage(content="Assistant.1", source="assistant"),
        UserMessage(content="User.2", source="user"),
        AssistantMessage(content="Assistant.2", source="assistant"),
    ]

    result = ensure_alternating_roles(messages)

    assert len(result) == 4
    assert result[0].content == "User.1"
    assert result[1].content == "Assistant.1"
    assert result[2].content == "User.2"
    assert result[3].content == "Assistant.2"


@pytest.mark.asyncio
async def test_ensure_alternating_roles_consecutive_user_messages() -> None:
    """Two consecutive user messages must be merged into one."""
    messages: List[LLMMessage] = [
        UserMessage(content="User.1", source="user"),
        UserMessage(content="User.2", source="user"),
        AssistantMessage(content="Assistant.1", source="assistant"),
    ]

    result = ensure_alternating_roles(messages)

    assert len(result) == 2
    assert isinstance(result[0], UserMessage)
    assert result[0].content == "User.1\n\nUser.2"
    assert isinstance(result[1], AssistantMessage)
    assert result[1].content == "Assistant.1"


@pytest.mark.asyncio
async def test_ensure_alternating_roles_consecutive_assistant_messages() -> None:
    """Two consecutive assistant messages must be merged into one."""
    messages: List[LLMMessage] = [
        UserMessage(content="User.1", source="user"),
        AssistantMessage(content="Assistant.1", source="assistant"),
        AssistantMessage(content="Assistant.2", source="assistant"),
        UserMessage(content="User.2", source="user"),
    ]

    result = ensure_alternating_roles(messages)

    assert len(result) == 3
    assert isinstance(result[0], UserMessage)
    assert result[0].content == "User.1"
    assert isinstance(result[1], AssistantMessage)
    assert result[1].content == "Assistant.1\n\nAssistant.2"
    assert isinstance(result[2], UserMessage)
    assert result[2].content == "User.2"


@pytest.mark.asyncio
async def test_ensure_alternating_roles_three_consecutive_same_role() -> None:
    """Three consecutive same-role messages must all be merged into one."""
    messages: List[LLMMessage] = [
        UserMessage(content="A", source="user"),
        UserMessage(content="B", source="user"),
        UserMessage(content="C", source="user"),
        AssistantMessage(content="X", source="assistant"),
        AssistantMessage(content="Y", source="assistant"),
    ]

    result = ensure_alternating_roles(messages)

    assert len(result) == 2
    assert isinstance(result[0], UserMessage)
    assert result[0].content == "A\n\nB\n\nC"
    assert isinstance(result[1], AssistantMessage)
    assert result[1].content == "X\n\nY"


@pytest.mark.asyncio
async def test_ensure_alternating_roles_system_messages_preserved() -> None:
    """SystemMessages must pass through unchanged and not affect role adjacency detection."""
    messages: List[LLMMessage] = [
        SystemMessage(content="System prompt"),
        UserMessage(content="User.1", source="user"),
        UserMessage(content="User.2", source="user"),
        AssistantMessage(content="Assistant.1", source="assistant"),
    ]

    result = ensure_alternating_roles(messages)

    assert len(result) == 3
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == "System prompt"
    assert isinstance(result[1], UserMessage)
    assert result[1].content == "User.1\n\nUser.2"
    assert isinstance(result[2], AssistantMessage)
    assert result[2].content == "Assistant.1"


@pytest.mark.asyncio
async def test_ensure_alternating_roles_empty_list() -> None:
    """An empty message list must be returned as-is."""
    result = ensure_alternating_roles([])
    assert result == []
