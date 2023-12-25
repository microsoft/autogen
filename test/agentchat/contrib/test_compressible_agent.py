import inspect
import pytest
import sys
import autogen
import os
from autogen.agentchat.contrib.compressible_agent import CompressibleAgent

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
    sys.platform in ["darwin", "win32"] or not OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_mode_compress():
    conversations = {}

    assistant = CompressibleAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 43,
            "config_list": config_list,
        },
        compress_config={
            "mode": "COMPRESS",
            "trigger_count": 600,
            "verbose": True,
        },
    )

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
        or x.get("content", "").rstrip().endswith("TERMINATE."),
        code_execution_config={"work_dir": here},
    )

    user_proxy.initiate_chat(
        assistant,
        message="Find all $x$ that satisfy the inequality $(2x+10)(x+3)<(3x+9)(x+8)$. Express your answer in interval notation.",
    )

    assistant.reset()
    print(conversations)


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or not OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_mode_customized():
    try:
        assistant = CompressibleAgent(
            name="assistant",
            llm_config={
                "timeout": 600,
                "cache_seed": 43,
                "config_list": config_list,
            },
            compress_config={
                "mode": "CUSTOMIZED",
            },
        )
    except ValueError:
        print("ValueError raised as expected.")

    def constrain_num_messages(messages):
        """Constrain the number of messages to 3.

        This is an example of a customized compression function.

        Returns:
            bool: whether the compression is successful.
            list: the compressed messages.
        """
        if len(messages) <= 3:
            # do nothing
            return False, None

        # save the first and last two messages
        return True, messages[:1] + messages[-2:]

    # create a CompressibleAgent instance named "assistant"
    assistant = CompressibleAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 43,
            "config_list": config_list,
            "model": "gpt-3.5-turbo",
        },
        compress_config={
            "mode": "CUSTOMIZED",
            "compress_function": constrain_num_messages,  # this is required for customized compression
            "trigger_count": 1000,
        },
    )

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
        or x.get("content", "").rstrip().endswith("TERMINATE."),
        code_execution_config={"work_dir": "web"},
        system_message="""Reply TERMINATE if the task has been solved at full satisfaction.
    Otherwise, reply CONTINUE, or the reason why the task is not solved yet.""",
    )

    user_proxy.initiate_chat(
        assistant,
        message="""Show me the YTD gain of 10 largest technology companies as of today.""",
    )


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or not OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_compress_message():
    assistant = CompressibleAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 43,
            "config_list": config_list,
        },
        compress_config={
            "mode": "COMPRESS",
            "trigger_count": 600,
            "verbose": True,
            "leave_last_n": 0,
        },
    )

    assert assistant.compress_messages([{"content": "hello world", "role": "user"}]) == (
        False,
        None,
    ), "Single message should not be compressed"

    is_success, _ = assistant.compress_messages(
        [
            {"content": "Hello!", "role": "user"},
            {"content": "How can I help you today?", "role": "assistant"},
            {"content": "Can you tell me a joke about programming?", "role": "assistant"},
        ]
    )
    assert is_success, "Compression failed."


def test_mode_terminate():
    assistant = CompressibleAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 43,
            "config_list": config_list,
        },
        compress_config=True,
    )

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        code_execution_config={"work_dir": "coding"},
    )

    final, _ = assistant.on_oai_token_limit(
        [
            {"content": "Hello!", "role": "user"},
            {"content": "How can I help you today?", "role": "assistant"},
            {"content": "1&" * 5000, "role": "assistant"},
        ],
        sender=user_proxy,
    )
    assert final, "Terminating the conversation at max token limit is not working."


@pytest.mark.parametrize(
    "messages, leave_last_n, compressed_prompt, expected",
    [
        # Primary thread test covering all message types
        (
            [
                {"role": "system", "content": "System message, skipped"},
                {"content": "compressed prompt: prior compressed content"},
                {"role": "user", "content": "Start"},
                {"role": "function", "name": "Function1", "content": "Content A"},
                {"role": "tool", "name": "Tool1", "tool_call_id": "123", "content": "Content B"},
                {"name": "User1", "role": "user", "content": "Content C"},
                {"role": "system", "content": "System message"},
                {"function_call": {"name": "Function2", "arguments": {"arg1": "value1"}}},
                {
                    "tool_calls": [
                        {
                            "id": "456",
                            "type": "function",
                            "function": {"name": "Function3", "arguments": {"arg2": "value2"}},
                        },
                        {
                            "id": "457",
                            "type": "function",
                            "function": {"name": "Function4", "arguments": {"arg3": "value3"}},
                        },
                    ]
                },
                {"role": "assistant", "content": "End"},
            ],
            1,
            "compressed prompt: ",
            [
                {
                    "role": "user",
                    "content": inspect.cleandoc(
                        """

                prior compressed content
                ##USER## Start
                ##FUNCTION_RETURN## (from function "Function1"):
                Content A
                ##TOOL_RETURN## (from tool "Tool1", tool call id "123"):
                Content B
                ##User1(USER)## Content C
                ##SYSTEM## System message
                ##FUNCTION_CALL##
                Name: Function2
                Args: {'arg1': 'value1'}
                ##TOOL_CALL## ToolCallId: 456
                Name: Function3
                Args: {'arg2': 'value2'}
                ##TOOL_CALL## ToolCallId: 457
                Name: Function4
                Args: {'arg3': 'value3'}
            """
                    )
                    + "\n",
                }
            ],
        ),
        ([], 0, "compress this", [{"role": "user", "content": ""}]),
    ],
)
def test_chat_messages_to_compress(messages, leave_last_n, compressed_prompt, expected):
    assistant = CompressibleAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 43,
            "config_list": config_list,
        },
        compress_config=True,
    )
    result = assistant.chat_messages_to_compress(messages, leave_last_n, compressed_prompt)
    assert result == expected, "Compressed messages is not correct."


if __name__ == "__main__":
    test_mode_compress()
    test_mode_customized()
    test_compress_message()
    test_mode_terminate()
