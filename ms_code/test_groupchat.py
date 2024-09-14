from typing import Any, Dict, List, Optional

import pytest

from autogen import Agent, AssistantAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.capabilities import transform_messages, transforms


def test_select_speaker_transform_messages():
    """Tests adding transform messages to a GroupChat for speaker selection when in 'auto' mode"""

    # Test adding a TransformMessages to a group chat
    test_add_transforms = transform_messages.TransformMessages(
        transforms=[
            transforms.MessageHistoryLimiter(max_messages=10),
            transforms.MessageTokenLimiter(max_tokens=3000, max_tokens_per_message=500, min_tokens=300),
        ]
    )

    print(GroupChat.__module__)  # Prints the module where GroupChat is defined
    import inspect

    # Get the file where GroupChat is defined
    print(inspect.getfile(GroupChat))

    coder = AssistantAgent(name="Coder", llm_config=None)
    groupchat = GroupChat(messages=[], agents=[coder], select_speaker_transform_messages=test_add_transforms)

    # Ensure the transform have been added to the GroupChat
    assert groupchat._speaker_selection_transforms == test_add_transforms

    # Attempt to add a non MessageTransforms object, such as a list of transforms
    with pytest.raises(ValueError, match="select_speaker_transform_messages must be None or MessageTransforms."):
        groupchat = GroupChat(
            messages=[],
            agents=[coder],
            select_speaker_transform_messages=List[transforms.MessageHistoryLimiter(max_messages=10)],
        )

    # Ensure if we don't pass any transforms in, none are on the GroupChat
    groupchat_missing = GroupChat(messages=[], agents=[coder])

    assert groupchat_missing._speaker_selection_transforms is None

    # Ensure we can pass in None
    groupchat_none = GroupChat(
        messages=[],
        agents=[coder],
        select_speaker_transform_messages=None,
    )

    assert groupchat_none._speaker_selection_transforms is None


test_select_speaker_transform_messages()
