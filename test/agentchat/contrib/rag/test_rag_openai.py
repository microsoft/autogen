import pytest
import os
import sys
import autogen
from autogen.agentchat.contrib.rag import RagAgent, logger

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from test_assistant_agent import OAI_CONFIG_LIST, KEY_LOC  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
def test_rag_openai():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        KEY_LOC,
        filter_dict={
            "model": "gpt-35-turbo",
        },
    )
    llm_config = {
        "timeout": 60,
        "config_list": config_list,
    }

    def termination_msg(x):
        return isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()

    userproxy = autogen.UserProxyAgent(
        name="userproxy",
        is_termination_msg=termination_msg,
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False, "work_dir": ".tmp"},
        default_auto_reply="Reply `TERMINATE` if the task is done.",
        description="The boss who ask questions and give tasks.",
    )

    rag_config = {
        "docs_path": "https://raw.githubusercontent.com/microsoft/autogen/main/README.md",
    }

    rag = RagAgent(
        name="rag",
        is_termination_msg=termination_msg,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        llm_config=llm_config,
        rag_config=rag_config,
        code_execution_config=False,
        description="Assistant who has extra content retrieval power for solving difficult problems.",
    )

    userproxy.initiate_chat(recipient=rag, message="What is AutoGen?")


if __name__ == "__main__":
    test_rag_openai()
