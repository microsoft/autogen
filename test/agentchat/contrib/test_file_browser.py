import os
import pytest
import sys

from autogen import UserProxyAgent, config_list_from_json
from autogen.cache import Cache
from autogen.file_browser import FileBrowserAgent
from autogen.oai.openai_utils import filter_config

import openai
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import MOCK_OPEN_AI_API_KEY, skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

if not skip_openai:
    config_list = config_list_from_json(env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC)

@pytest.mark.skipif(
    skip_openai,
    reason="do not run if openai is not installed",
)
def test_file_browser_oai() -> None:
    llm_config = {"config_list": config_list, "timeout": 180, "cache_seed": 42}

    # adding Azure name variations to the model list
    model = ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-16k", "gpt-4"]
    model += [m.replace(".", "") for m in model]

    summarizer_llm_config = {
        "config_list": filter_config(config_list, dict(model=model)),  # type: ignore[no-untyped-call]
        "timeout": 180,
    }

    assert len(llm_config["config_list"]) > 0  # type: ignore[arg-type]
    assert len(summarizer_llm_config["config_list"]) > 0

    page_size = 4096

    file_browser = FileBrowserAgent(
        "file_browser",
        llm_config=llm_config,
        summarizer_llm_config=summarizer_llm_config,
        file_browser_config={} # TODO: update the file size?
    )
    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
        default_auto_reply="",
        is_termination_msg=lambda x: True,
    )

    with Cache.disk():
        user_proxy.initiate_chat(file_browser, message="Please open file: ../../test_files/example.pdf")

        user_proxy.initiate_chat(file_browser, message="What's this file about?")

        user_proxy.initiate_chat(file_browser, message="what's the primary purpose of autogen?")

        # user_proxy.initiate_chat(file_browser, message="Please scroll down.")

        # user_proxy.initiate_chat(file_browser, message="Please scroll up.")
