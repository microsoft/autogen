import os
import sys
import re
import tempfile
import pytest
from autogen.agentchat import UserProxyAgent
from autogen.agentchat.contrib.content_agent import ContentAgent
from autogen.oai.openai_utils import filter_config, config_list_from_json
from autogen.cache import Cache

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import MOCK_OPEN_AI_API_KEY, skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip_oai = True
else:
    skip_oai = False or skip_openai

if not skip_oai:
    config_list = config_list_from_json(env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC)


@pytest.mark.skipif(
    skip_oai,
    reason="do not run if oai is not installed",
)
def test_content_agent(browser: str) -> None:
    llm_config = {"config_list": config_list, "timeout": 180, "cache_seed": 42}

    model = ["gpt-3.5-turbo"]
    model += [m.replace(".", "") for m in model]

    # model = ['dolphin-mistral:7b-v2.6-q8_0']
    assert len(llm_config["config_list"]) > 0  # type: ignore[arg-type]

    # Define the temporary storage location
    temporary_content_storage = os.path.join(tempfile.gettempdir(), "test_content_agent_storage")
    print(f"Storing temporary test files in {temporary_content_storage}")

    # Define the system message for the ContentAgent
    content_agent_system_msg = "You are data collection agent specializing in content on the web."

    # Instantiate the ContentAgent
    content_agent = ContentAgent(
        name="ContentAgent",
        system_message=content_agent_system_msg,
        llm_config=llm_config,
        max_consecutive_auto_reply=0,
        silent=False,
        # Below are the arguments specific to the ContentAgent
        storage_path=temporary_content_storage,
        browser_kwargs={"browser": browser},
        max_depth=0,
    )

    # Instantiate the User Proxy Agent
    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
        default_auto_reply="",
        is_termination_msg=lambda x: True,
    )

    # Register the collection process as the default reply to the user
    content_agent.register_reply(user_proxy, content_agent.collect_content)

    # Define the links used during the testing process
    links = [
        "https://microsoft.github.io/autogen/docs/Examples",
        "https://microsoft.github.io/autogen/docs/Getting-Started",
        "https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/",
    ]

    with Cache.disk():
        for link in links:
            # Collect the content from the requested link
            user_proxy.initiate_chat(content_agent, message=link)

            assert (
                content_agent.process_history[link]["url"] == link
            ), "Investigate why the correct not link was reported"

            assert os.path.exists(
                content_agent.process_history[link]["local_path"]
            ), "The content storage path was not found"

            assert len(content_agent.process_history[link]["content"]) > 0, "No content was identified or stored"

            assert os.path.exists(
                os.path.join(content_agent.process_history[link]["local_path"], "content.txt")
            ), "The file path for content.txt was not found"

            assert os.path.exists(
                os.path.join(content_agent.process_history[link]["local_path"], "metadata.txt")
            ), "The file path for metadata.txt was not found"

            assert os.path.exists(
                os.path.join(content_agent.process_history[link]["local_path"], "index.html")
            ), "The file path for index.html was not found"

            assert os.path.exists(
                os.path.join(content_agent.process_history[link]["local_path"], "screenshot.png")
            ), "The file path for screenshot.png was not found"

            assert os.path.exists(
                os.path.join(content_agent.process_history[link]["local_path"], "links.txt")
            ), "The file path for links.txt was not found"

            assert (
                os.path.getsize(os.path.join(content_agent.process_history[link]["local_path"], "links.txt")) > 0
            ), "The file size of links.txt was zero"
            assert (
                os.path.getsize(os.path.join(content_agent.process_history[link]["local_path"], "content.txt")) > 0
            ), "The file size of content.txt was zero"
            assert (
                os.path.getsize(os.path.join(content_agent.process_history[link]["local_path"], "metadata.txt")) > 0
            ), "The file size of metadata.txt was zero"
            assert (
                os.path.getsize(os.path.join(content_agent.process_history[link]["local_path"], "index.html")) > 0
            ), "The file size of index.html was zero"
            assert (
                os.path.getsize(os.path.join(content_agent.process_history[link]["local_path"], "screenshot.png")) > 0
            ), "The file size of screenshot.png was zero"

    print()
    print(f"All done, feel free to browse the collected content at: {temporary_content_storage}")


if __name__ == "__main__":
    """Runs this file's tests from the command line."""

    if not skip_oai:
        test_content_agent(browser="firefox")
