#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest

import autogen

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import reason, skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

try:
    import chromadb
    import openai
    from chromadb.utils import embedding_functions as ef

    from autogen import AssistantAgent
    from autogen.agentchat.contrib.retrieve_user_proxy_agent import (
        RetrieveUserProxyAgent,
    )
except ImportError:
    skip = True
else:
    skip = False

reason = "do not run on MacOS or windows OR dependency is not installed OR " + reason


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip or skip_openai,
    reason=reason,
)
def test_retrievechat():
    conversations = {}
    # autogen.ChatCompletion.start_logging(conversations)  # deprecated in v0.2

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant.",
        llm_config={
            "timeout": 600,
            "seed": 42,
            "config_list": config_list,
        },
    )

    sentence_transformer_ef = ef.SentenceTransformerEmbeddingFunction()
    ragproxyagent = RetrieveUserProxyAgent(
        name="ragproxyagent",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        retrieve_config={
            "docs_path": "./website/docs",
            "chunk_token_size": 2000,
            "model": config_list[0]["model"],
            "client": chromadb.PersistentClient(path="/tmp/chromadb"),
            "embedding_function": sentence_transformer_ef,
            "get_or_create": True,
        },
    )

    assistant.reset()

    code_problem = "How can I use FLAML to perform a classification task, set use_spark=True, train 30 seconds and force cancel jobs if time limit is reached."
    ragproxyagent.initiate_chat(
        assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark", silent=True
    )

    print(conversations)


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip,
    reason=reason,
)
def test_retrieve_config():
    # test warning message when no docs_path is provided
    ragproxyagent = RetrieveUserProxyAgent(
        name="ragproxyagent",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        retrieve_config={
            "chunk_token_size": 2000,
            "get_or_create": True,
        },
    )
    assert ragproxyagent._docs_path is None


if __name__ == "__main__":
    # test_retrievechat()
    test_retrieve_config()
