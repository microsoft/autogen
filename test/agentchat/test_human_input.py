import autogen
import pytest
from unittest.mock import MagicMock
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
def test_get_human_input():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        max_consecutive_auto_reply=2,
        llm_config={"timeout": 600, "cache_seed": 41, "config_list": config_list, "temperature": 0},
    )

    user_proxy = autogen.UserProxyAgent(name="user", human_input_mode="ALWAYS", code_execution_config=False)

    # Use MagicMock to create a mock get_human_input function
    user_proxy.get_human_input = MagicMock(return_value="This is a test")

    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.a_check_termination_and_human_reply)

    user_proxy.initiate_chat(assistant, clear_history=True, message="Hello.")
    # Test without supplying messages parameter
    user_proxy.initiate_chat(assistant, clear_history=True)

    # Assert that custom_a_get_human_input was called at least once
    user_proxy.get_human_input.assert_called()


if __name__ == "__main__":
    test_get_human_input()
