#!/usr/bin/env python3 -m pytest

import asyncio
import json
import os
import re
from json import dumps
from math import ceil
from typing import Mapping

import pytest
from autogen_core import AgentId, AgentProxy, FunctionCall, SingleThreadedAgentRuntime
from autogen_core.models import (
    UserMessage,
)
from autogen_core.models._model_client import ChatCompletionClient
from autogen_core.tools._base import ToolSchema
from autogen_magentic_one.agents.multimodal_web_surfer import MultimodalWebSurfer
from autogen_magentic_one.agents.multimodal_web_surfer.tool_definitions import (
    TOOL_PAGE_DOWN,
    TOOL_PAGE_UP,
    TOOL_READ_PAGE_AND_ANSWER,
    TOOL_SUMMARIZE_PAGE,
    TOOL_VISIT_URL,
    TOOL_WEB_SEARCH,
)
from autogen_magentic_one.agents.orchestrator import RoundRobinOrchestrator
from autogen_magentic_one.agents.user_proxy import UserProxy
from autogen_magentic_one.messages import BroadcastMessage
from conftest import MOCK_CHAT_COMPLETION_KWARGS, reason
from openai import AuthenticationError

pytest_plugins = ("pytest_asyncio",)


BLOG_POST_URL = "https://microsoft.github.io/autogen/blog/2023/04/21/LLM-tuning-math"
BLOG_POST_TITLE = "Does Model and Inference Parameter Matter in LLM Applications? - A Case Study for MATH | AutoGen"
BING_QUERY = "Microsoft"
DEBUG_DIR = "test_logs_web_surfer_autogen"

skip_all = False

# except ImportError:
#    skip_all = True
# else:
#    skip_all = False

# try:
#    BING_API_KEY = os.environ["BING_API_KEY"]
# except KeyError:
#    skip_bing = True
# else:
#    skip_bing = False
# Search currently does not require an API key
skip_bing = False

if os.getenv("CHAT_COMPLETION_CLIENT_CONFIG"):
    skip_openai = False
else:
    skip_openai = True


def _rm_folder(path: str) -> None:
    """Remove all the regular files in a folder, then deletes the folder. Assumes a flat file structure, with no subdirectories."""
    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if os.path.isfile(fpath):
            os.unlink(fpath)
    os.rmdir(path)


def _create_logs_dir() -> None:
    logs_dir = os.path.join(os.getcwd(), DEBUG_DIR)
    if os.path.isdir(logs_dir):
        _rm_folder(logs_dir)
    os.mkdir(logs_dir)


def generate_tool_request(tool: ToolSchema, args: Mapping[str, str]) -> list[FunctionCall]:
    ret = [FunctionCall(id="", arguments="", name=tool["name"])]
    ret[0].arguments = dumps(args)
    return ret


async def make_browser_request(browser: MultimodalWebSurfer, tool: ToolSchema, args: Mapping[str, str] = {}) -> str:
    rects = await browser._get_interactive_rects()  # type: ignore

    req = generate_tool_request(tool, args)
    return str((await browser._execute_tool(req, rects, "", use_ocr=False))[1][0])  # type: ignore


# @pytest.mark.skipif(
#     skip_all,
#     reason="do not run if dependency is not installed",
# )
@pytest.mark.skip(reason="Need to fix this test to use a local website instead of a public one.")
@pytest.mark.asyncio
async def test_web_surfer() -> None:
    runtime = SingleThreadedAgentRuntime()
    # Create an appropriate client
    config = {"provider": "OpenAIChatCompletionClient", "config": json.loads(MOCK_CHAT_COMPLETION_KWARGS)}
    client = ChatCompletionClient.load_component(config)

    # Register agents.

    # Register agents.
    await MultimodalWebSurfer.register(
        runtime,
        "WebSurfer",
        lambda: MultimodalWebSurfer(),
    )
    web_surfer = AgentId("WebSurfer", "default")
    runtime.start()

    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer, MultimodalWebSurfer)
    await actual_surfer.init(
        model_client=client, downloads_folder=os.getcwd(), browser_channel="chromium", debug_dir=DEBUG_DIR
    )

    # Test some basic navigations
    tool_resp = await make_browser_request(actual_surfer, TOOL_VISIT_URL, {"url": BLOG_POST_URL})
    metadata = await actual_surfer._get_page_metadata()  # type: ignore
    assert f"{BLOG_POST_URL}".strip() in metadata["meta_tags"]["og:url"]
    assert f"{BLOG_POST_TITLE}".strip() in metadata["meta_tags"]["og:title"]

    # Get the % of the page the viewport shows so we can check it scrolled down properly
    m = re.search(r"\bThe viewport shows (\d+)% of the webpage", tool_resp)
    assert m is not None
    viewport_percentage = int(m.group(1))

    tool_resp = await make_browser_request(actual_surfer, TOOL_PAGE_DOWN)
    assert (
        f"The viewport shows {viewport_percentage}% of the webpage, and is positioned {viewport_percentage}% down from the top of the page."
        in tool_resp
    )  # Assumes the content is longer than one screen

    tool_resp = await make_browser_request(actual_surfer, TOOL_PAGE_UP)
    assert (
        f"The viewport shows {viewport_percentage}% of the webpage, and is positioned at the top of the page"
        in tool_resp
    )  # Assumes the content is longer than one screen

    #        # Try to scroll too far back up
    tool_resp = await make_browser_request(actual_surfer, TOOL_PAGE_UP)
    assert (
        f"The viewport shows {viewport_percentage}% of the webpage, and is positioned at the top of the page"
        in tool_resp
    )

    # Try to scroll too far down
    total_pages = ceil(100 / viewport_percentage)
    for _ in range(0, total_pages + 1):
        tool_resp = await make_browser_request(actual_surfer, TOOL_PAGE_DOWN)
    assert (
        f"The viewport shows {viewport_percentage}% of the webpage, and is positioned at the bottom of the page"
        in tool_resp
    )

    # Test Q&A and summarization -- we don't have a key so we expect it to fail #(but it means the code path is correct)
    with pytest.raises(AuthenticationError):
        tool_resp = await make_browser_request(
            actual_surfer, TOOL_READ_PAGE_AND_ANSWER, {"question": "When was it founded?"}
        )

    with pytest.raises(AuthenticationError):
        tool_resp = await make_browser_request(actual_surfer, TOOL_SUMMARIZE_PAGE)
    await runtime.stop_when_idle()


@pytest.mark.skipif(
    skip_all or skip_openai,
    reason="dependency is not installed OR" + reason,
)
@pytest.mark.asyncio
async def test_web_surfer_oai() -> None:
    runtime = SingleThreadedAgentRuntime()

    # Create an appropriate client
    client = ChatCompletionClient.load_component(json.loads(os.environ["CHAT_COMPLETION_CLIENT_CONFIG"]))

    # Register agents.
    await MultimodalWebSurfer.register(
        runtime,
        "WebSurfer",
        lambda: MultimodalWebSurfer(),
    )
    web_surfer = AgentProxy(AgentId("WebSurfer", "default"), runtime)

    await UserProxy.register(
        runtime,
        "UserProxy",
        lambda: UserProxy(),
    )
    user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)
    await RoundRobinOrchestrator.register(
        runtime, "orchestrator", lambda: RoundRobinOrchestrator([web_surfer, user_proxy])
    )
    runtime.start()

    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer.id, MultimodalWebSurfer)
    await actual_surfer.init(
        model_client=client, downloads_folder=os.getcwd(), browser_channel="chromium", debug_dir=DEBUG_DIR
    )

    await runtime.send_message(
        BroadcastMessage(
            content=UserMessage(
                content="Please visit the page 'https://en.wikipedia.org/wiki/Microsoft'", source="user"
            )
        ),
        recipient=web_surfer.id,
        sender=user_proxy.id,
    )
    await runtime.send_message(
        BroadcastMessage(content=UserMessage(content="Please scroll down.", source="user")),
        recipient=web_surfer.id,
        sender=user_proxy.id,
    )
    await runtime.send_message(
        BroadcastMessage(content=UserMessage(content="Please scroll up.", source="user")),
        recipient=web_surfer.id,
        sender=user_proxy.id,
    )
    await runtime.send_message(
        BroadcastMessage(content=UserMessage(content="When was it founded?", source="user")),
        recipient=web_surfer.id,
        sender=user_proxy.id,
    )
    await runtime.send_message(
        BroadcastMessage(content=UserMessage(content="What's this page about?", source="user")),
        recipient=web_surfer.id,
        sender=user_proxy.id,
    )
    await runtime.stop_when_idle()


@pytest.mark.skipif(
    skip_bing,
    reason="do not run if bing api key is not available",
)
@pytest.mark.asyncio
async def test_web_surfer_bing() -> None:
    runtime = SingleThreadedAgentRuntime()
    # Create an appropriate client
    config = {"provider": "OpenAIChatCompletionClient", "config": json.loads(MOCK_CHAT_COMPLETION_KWARGS)}
    client = ChatCompletionClient.load_component(config)

    # Register agents.
    await MultimodalWebSurfer.register(
        runtime,
        "WebSurfer",
        lambda: MultimodalWebSurfer(),
    )
    web_surfer = AgentProxy(AgentId("WebSurfer", "default"), runtime)

    runtime.start()
    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer.id, MultimodalWebSurfer)
    await actual_surfer.init(
        model_client=client, downloads_folder=os.getcwd(), browser_channel="chromium", debug_dir=DEBUG_DIR
    )

    # Test some basic navigations
    tool_resp = await make_browser_request(actual_surfer, TOOL_WEB_SEARCH, {"query": BING_QUERY})

    metadata = await actual_surfer._get_page_metadata()  # type: ignore
    assert f"{BING_QUERY}".strip() in metadata["meta_tags"]["og:url"]
    assert f"{BING_QUERY}".strip() in metadata["meta_tags"]["og:title"]
    assert f"I typed '{BING_QUERY}' into the browser search bar." in tool_resp.replace("\\", "")

    tool_resp = await make_browser_request(actual_surfer, TOOL_WEB_SEARCH, {"query": BING_QUERY + " Wikipedia"})
    markdown = await actual_surfer._get_page_markdown()  # type: ignore
    assert "https://en.wikipedia.org/wiki/" in markdown
    await runtime.stop_when_idle()
    # remove the logs directory
    _rm_folder(DEBUG_DIR)


if __name__ == "__main__":
    """Runs this file's tests from the command line."""

    _create_logs_dir()
    asyncio.run(test_web_surfer())
    asyncio.run(test_web_surfer_oai())
    # IMPORTANT: last test should remove the logs directory
    asyncio.run(test_web_surfer_bing())
