#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest
from sentence_transformers import SentenceTransformer

from autogen import AssistantAgent, config_list_from_json

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

try:
    import pgvector

    from autogen.agentchat.contrib.retrieve_user_proxy_agent import (
        RetrieveUserProxyAgent,
    )
except ImportError:
    skip = True
else:
    skip = False


test_dir = os.path.join(os.path.dirname(__file__), "../../..", "test_files")


@pytest.mark.skipif(
    skip or skip_openai,
    reason="dependency is not installed OR requested to skip",
)
def test_retrievechat():
    conversations = {}
    # ChatCompletion.start_logging(conversations)  # deprecated in v0.2

    config_list = config_list_from_json(
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

    sentence_transformer_ef = SentenceTransformer("all-MiniLM-L6-v2").encode
    ragproxyagent = RetrieveUserProxyAgent(
        name="ragproxyagent",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        retrieve_config={
            "task": "code",
            "docs_path": [
                "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Examples/Integrate%20-%20Spark.md",
                "https://raw.githubusercontent.com/microsoft/FLAML/main/website/docs/Research.md",
                "https://raw.githubusercontent.com/Knuckles-Team/geniusbot/main/README.md",
                "https://raw.githubusercontent.com/Knuckles-Team/repository-manager/main/README.md",
                "https://raw.githubusercontent.com/Knuckles-Team/gitlab-api/main/README.md",
                "https://raw.githubusercontent.com/Knuckles-Team/media-downloader/main/README.md",
                os.path.join(os.path.abspath(""), "..", "website", "docs"),
            ],
            "custom_text_types": ["non-existent-type"],
            "chunk_token_size": 2000,
            "model": config_list[0]["model"],
            "vector_db": "pgvector",  # PGVector database
            "collection_name": "test_collection",
            "db_config": {
                "connection_string": "postgresql://postgres:postgres@localhost:5432/postgres",
            },
            "embedding_function": sentence_transformer_ef,
            "get_or_create": True,  # set to False if you don't want to reuse an existing collection
            "overwrite": False,  # set to True if you want to overwrite an existing collection
        },
        code_execution_config=False,  # set to False if you don't want to execute the code
    )

    assistant.reset()

    code_problem = "How can I use FLAML to perform a classification task, set use_spark=True, train 30 seconds and force cancel jobs if time limit is reached."
    ragproxyagent.initiate_chat(
        assistant, message=ragproxyagent.message_generator, problem=code_problem, search_string="spark", silent=True
    )

    print(conversations)


if __name__ == "__main__":
    test_retrievechat()
