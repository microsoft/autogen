import sys

import os
import pytest
from autogen import config_list_from_json

try:
    import openai
    from autogen.agentchat.contrib.profiler import (
        state_space_to_str,
        annotate_message,
        annotate_chat_history,
        EXAMPLE_STATE_SPACE,
    )
except ImportError:
    skip = True
else:
    skip = False


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import OAI_CONFIG_LIST, KEY_LOC  # noqa: E402


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip is True,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_state_space_to_str():
    # Test the state_space_to_str function
    result = state_space_to_str(EXAMPLE_STATE_SPACE, filter_by_role=None)
    assert isinstance(result, str), "Expected result to be a string"

    result = state_space_to_str(EXAMPLE_STATE_SPACE, filter_by_role="user")
    assert isinstance(result, str), "Expected result to be a string"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip is True,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_annotate_message():
    # Test the annotate_message function
    role = "user"
    content = "Please write a program to print hello world"
    state_space = EXAMPLE_STATE_SPACE
    llm_config = config_list_from_json(OAI_CONFIG_LIST, file_location=KEY_LOC)[0]
    result = annotate_message(role, content, state_space, llm_config=llm_config)
    assert isinstance(result, list), "Expected result to be a list of strings"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip is True,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_annotate_chat_history():
    # Test the annotate_chat_history function
    chat_history = [{"role": "user", "content": "Write a program to print hello world"}]
    state_space = EXAMPLE_STATE_SPACE
    llm_config = config_list_from_json(OAI_CONFIG_LIST, file_location=KEY_LOC)[0]
    result = annotate_chat_history(chat_history, state_space, llm_config=llm_config)
    assert isinstance(result, list), "Expected result to be a list"
