from typing import List

import pytest
from autogen_agentchat.utils import remove_images
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
