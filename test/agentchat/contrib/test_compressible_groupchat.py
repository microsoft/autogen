import pytest
import sys
import autogen
import os
from autogen.agentchat.contrib.compressible_groupchatmanager import CompressibleGroupChatManager

here = os.path.abspath(os.path.dirname(__file__))
KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


config_list = autogen.config_list_from_json(
    OAI_CONFIG_LIST,
    file_location=KEY_LOC,
    filter_dict={
        "model": ["gpt-3.5-turbo", "gpt-35-turbo", "gpt-3.5-turbo-16k", "gpt-35-turbo-16k"],
    },
)

try:
    import openai

    OPENAI_INSTALLED = True
except ImportError:
    OPENAI_INSTALLED = False


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run if dependency is not installed",
)
def test_compressible_groupchat():
    llm_config = {"config_list": config_list, "cache_seed": 42}
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        code_execution_config={"last_n_messages": 2, "work_dir": "groupchat"},
        human_input_mode="TERMINATE",
    )
    coder = autogen.AssistantAgent(
        name="Coder",
        llm_config=llm_config,
    )
    pm = autogen.AssistantAgent(
        name="Product_manager",
        system_message="Creative in software product ideas.",
        llm_config=llm_config,
    )

    groupchat = autogen.GroupChat(agents=[user_proxy, coder, pm], messages=[], max_round=10)

    # replace GroupChatManager with CompressibleGroupChatManager
    # manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
    manager = CompressibleGroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        compress_config={
            "mode": "COMPRESS",
            "trigger_count": 1000,
            "leave_last_n": 2,  # leave last n messages uncompressed
            "verbose": False,  # to allow printing of compression information
        },
    )
    user_proxy.initiate_chat(
        manager, message="Find a latest paper about gpt-4 on arxiv and find its potential applications in software."
    )


def test_convert_message():
    llm_config = {"config_list": config_list, "cache_seed": 42}
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        code_execution_config={"last_n_messages": 2, "work_dir": "groupchat"},
        human_input_mode="TERMINATE",
    )

    groupchat = autogen.GroupChat(agents=[user_proxy], messages=[], max_round=10)

    manager = CompressibleGroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        compress_config={
            "mode": "COMPRESS",
            "trigger_count": 2000,
            "leave_last_n": 2,  # leave last n messages uncompressed
            "verbose": False,  # to allow printing of compression information
        },
    )

    messages = [
        {"content": "Hello!", "role": "user", "name": "User_proxy"},
        {"content": "Hello!", "role": "user", "name": "Coder"},
        {"content": "How can I help you today?", "role": "system"},
        {
            "content": "Can you tell me a joke about programming?",
            "function_call": {"name": "get_joke", "parameters": {"topic": "programming"}},
            "role": "user",
        },
    ]

    converted = manager._convert_agent_messages(messages, user_proxy)

    for c in converted:
        print(c)
    assert converted[0]["role"] == "assistant", "Error in _convert_agent_messages"
    assert "name" not in converted[0], "name should be removed from messages after _convert_agent_messages."
    assert converted[1]["role"] == "user", "Error in _convert_agent_messages"
    assert converted[2]["role"] == "system", "System role should not be changed."
    assert converted[3]["role"] == "assistant", "function_call should be converted to assistant role."


if __name__ == "__main__":
    test_compressible_groupchat()
    test_convert_message()
