import os
import sys
import tempfile
from typing import Any, Dict, List, Union

import pytest

import autogen
from autogen.agentchat.contrib.capabilities.transform_messages import TransformMessages
from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter, MessageTokenLimiter

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402


@pytest.mark.skipif(skip_openai, reason="Requested to skip openai test.")
def test_transform_messages_capability():
    """Test the TransformMessages capability to handle long contexts.

    This test is a replica of test_transform_chat_history_with_agents in test_context_handling.py
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        config_list = autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            KEY_LOC,
            filter_dict={
                "model": "gpt-3.5-turbo",
            },
        )

        assistant = autogen.AssistantAgent(
            "assistant", llm_config={"config_list": config_list}, max_consecutive_auto_reply=1
        )

        context_handling = TransformMessages(
            transforms=[
                MessageHistoryLimiter(max_messages=10),
                MessageTokenLimiter(max_tokens=10, max_tokens_per_message=5),
            ]
        )
        context_handling.add_to_agent(assistant)
        user = autogen.UserProxyAgent(
            "user",
            code_execution_config={"work_dir": temp_dir},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            max_consecutive_auto_reply=1,
        )

        # Create a very long chat history that is bound to cause a crash
        # for gpt 3.5
        for i in range(1000):
            assitant_msg = {"role": "assistant", "content": "test " * 1000}
            user_msg = {"role": "user", "content": ""}

            assistant.send(assitant_msg, user, request_reply=False)
            user.send(user_msg, assistant, request_reply=False)

        try:
            user.initiate_chat(
                assistant,
                message="Plot a chart of nvidia and tesla stock prices for the last 5 years",
                clear_history=False,
            )
        except Exception as e:
            assert False, f"Chat initiation failed with error {str(e)}"


if __name__ == "__main__":
    test_transform_messages_capability()
