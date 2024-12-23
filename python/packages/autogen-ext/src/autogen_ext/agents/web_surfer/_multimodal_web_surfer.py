import base64
import hashlib
import io
import json
import logging
import os
import re
import time
import traceback
from typing import (
    Any,
    AsyncGenerator,
    BinaryIO,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    cast,
)
from urllib.parse import quote_plus

import aiofiles
import PIL.Image
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentEvent, ChatMessage, MultiModalMessage, TextMessage
from autogen_core import EVENT_LOGGER_NAME, CancellationToken, FunctionCall
from autogen_core import Image as AGImage
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from PIL import Image
from playwright.async_api import BrowserContext, Download, Page, Playwright, async_playwright

from ._events import WebSurferEvent
from ._prompts import WEB_SURFER_OCR_PROMPT, WEB_SURFER_QA_PROMPT, WEB_SURFER_QA_SYSTEM_MESSAGE, WEB_SURFER_TOOL_PROMPT
from ._set_of_mark import add_set_of_mark
from ._tool_definitions import (
    TOOL_CLICK,
    TOOL_HISTORY_BACK,
    TOOL_HOVER,
    TOOL_PAGE_DOWN,
    TOOL_PAGE_UP,
    TOOL_READ_PAGE_AND_ANSWER,
    TOOL_SLEEP,
    TOOL_SUMMARIZE_PAGE,
    TOOL_TYPE,
    TOOL_VISIT_URL,
    TOOL_WEB_SEARCH,
)
from ._types import InteractiveRegion, UserContent
from ._utils import message_content_to_str
from .playwright_controller import PlaywrightController


class MultimodalWebSurfer(BaseChatAgent):
    """
    MultimodalWebSurfer is a multimodal agent that acts as a web surfer that can search the web and visit web pages.

    It launches a chromium browser and allows the playwright to interact with the web browser and can perform a variety of actions. The browser is launched on the first call to the agent and is reused for subsequent calls.

    It must be used with a multimodal model client that supports function/tool calling, ideally GPT-4o currently.


    When :meth:`on_messages` or :meth:`on_messages_stream` is called, the following occurs:
        1) If this is the first call, the browser is initialized and the page is loaded. This is done in :meth:`_lazy_init`. The browser is only closed when :meth:`close` is called.
        2) The method :meth:`_generate_reply` is called, which then creates the final response as below.
        3) The agent takes a screenshot of the page, extracts the interactive elements, and prepares a set-of-mark screenshot with bounding boxes around the interactive elements.
        4) The agent makes a call to the :attr:`model_client` with the SOM screenshot, history of messages, and the list of available tools.
            - If the model returns a string, the agent returns the string as the final response.
            - If the model returns a list of tool calls, the agent executes the tool calls with :meth:`_execute_tool` using :attr:`_playwright_controller`.
            - The agent returns a final response which includes a screenshot of the page, page metadata, description of the action taken and the inner text of the webpage.
        5) If at any point the agent encounters an error, it returns the error message as the final response.


    .. note::
        Please note that using the MultimodalWebSurfer involves interacting with a digital world designed for humans, which carries inherent risks.
        Be aware that agents may occasionally attempt risky actions, such as recruiting humans for help or accepting cookie agreements without human involvement. Always ensure agents are monitored and operate within a controlled environment to prevent unintended consequences.
        Moreover, be cautious that MultimodalWebSurfer may be susceptible to prompt injection attacks from webpages.

    Args:
        name (str): The name of the agent.
        model_client (ChatCompletionClient): The model client used by the agent. Must be multimodal and support function calling.
        downloads_folder (str, optional): The folder where downloads are saved. Defaults to None, no downloads are saved.
        description (str, optional): The description of the agent. Defaults to MultimodalWebSurfer.DEFAULT_DESCRIPTION.
        debug_dir (str, optional): The directory where debug information is saved. Defaults to None.
        headless (bool, optional): Whether the browser should be headless. Defaults to True.
        start_page (str, optional): The start page for the browser. Defaults to MultimodalWebSurfer.DEFAULT_START_PAGE.
        animate_actions (bool, optional): Whether to animate actions. Defaults to False.
        to_save_screenshots (bool, optional): Whether to save screenshots. Defaults to False.
        use_ocr (bool, optional): Whether to use OCR. Defaults to True.
        browser_channel (str, optional): The browser channel. Defaults to None.
        browser_data_dir (str, optional): The browser data directory. Defaults to None.
        to_resize_viewport (bool, optional): Whether to resize the viewport. Defaults to True.
        playwright (Playwright, optional): The playwright instance. Defaults to None.
        context (BrowserContext, optional): The browser context. Defaults to None.




    Example usage:

    The following example demonstrates how to create a web surfing agent with
    a model client and run it for multiple turns.

        .. code-block:: python


            import asyncio
            from autogen_agentchat.ui import Console
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.agents.web_surfer import MultimodalWebSurfer


            async def main() -> None:
                # Define an agent
                web_surfer_agent = MultimodalWebSurfer(
                    name="MultimodalWebSurfer",
                    model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-08-06"),
                )

                # Define a team
                agent_team = RoundRobinGroupChat([web_surfer_agent], max_turns=3)

                # Run the team and stream messages to the console
                stream = agent_team.run_stream(task="Navigate to the AutoGen readme on GitHub.")
                await Console(stream)
                # Close the browser controlled by the agent
                await web_surfer_agent.close()


            asyncio.run(main())
    """

    DEFAULT_DESCRIPTION = """
    A helpful assistant with access to a web browser.
    Ask them to perform web searches, open pages, and interact with content (e.g., clicking links, scrolling the viewport, etc., filling in form fields, etc.).
    It can also summarize the entire page, or answer questions based on the content of the page.
    It can also be asked to sleep and wait for pages to load, in cases where the pages seem to be taking a while to load.
    """
    DEFAULT_START_PAGE = "https://www.bing.com/"

    # Viewport dimensions
    VIEWPORT_HEIGHT = 900
    VIEWPORT_WIDTH = 1440

    # Size of the image we send to the MLM
    # Current values represent a 0.85 scaling to fit within the GPT-4v short-edge constraints (768px)
    MLM_HEIGHT = 765
    MLM_WIDTH = 1224

    SCREENSHOT_TOKENS = 1105

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        downloads_folder: str | None = None,
        description: str = DEFAULT_DESCRIPTION,
        debug_dir: str | None = None,
        headless: bool = True,
        start_page: str | None = DEFAULT_START_PAGE,
        animate_actions: bool = False,
        to_save_screenshots: bool = False,
        use_ocr: bool = True,
        browser_channel: str | None = None,
        browser_data_dir: str | None = None,
        to_resize_viewport: bool = True,
        playwright: Playwright | None = None,
        context: BrowserContext | None = None,
    ):
        """
        Initialize the MultimodalWebSurfer.
        """
        super().__init__(name, description)
        if debug_dir is None and to_save_screenshots:
            raise ValueError(
                "Cannot save screenshots without a debug directory. Set it using the 'debug_dir' parameter. The debug directory is created if it does not exist."
            )
        if model_client.capabilities["function_calling"] is False:
            raise ValueError(
                "The model does not support function calling. MultimodalWebSurfer requires a model that supports function calling."
            )
        if model_client.capabilities["vision"] is False:
            raise ValueError("The model is not multimodal. MultimodalWebSurfer requires a multimodal model.")
        self._model_client = model_client
        self.headless = headless
        self.browser_channel = browser_channel
        self.browser_data_dir = browser_data_dir
        self.start_page = start_page or self.DEFAULT_START_PAGE
        self.downloads_folder = downloads_folder
        self.debug_dir = debug_dir
        self.to_save_screenshots = to_save_screenshots
        self.use_ocr = use_ocr
        self.to_resize_viewport = to_resize_viewport
        self.animate_actions = animate_actions

        # Call init to set these in case not set
        self._playwright: Playwright | None = playwright
        self._context: BrowserContext | None = context
        self._page: Page | None = None
        self._last_download: Download | None = None
        self._prior_metadata_hash: str | None = None
        self.logger = logging.getLogger(EVENT_LOGGER_NAME + f".{self.name}.MultimodalWebSurfer")
        self._chat_history: List[LLMMessage] = []

        # Define the download handler
        def _download_handler(download: Download) -> None:
            self._last_download = download

        self._download_handler = _download_handler

        # Define the Playwright controller that handles the browser interactions
        self._playwright_controller = PlaywrightController(
            animate_actions=self.animate_actions,
            downloads_folder=self.downloads_folder,
            viewport_width=self.VIEWPORT_WIDTH,
            viewport_height=self.VIEWPORT_HEIGHT,
            _download_handler=self._download_handler,
            to_resize_viewport=self.to_resize_viewport,
        )
        self.default_tools = [
            TOOL_VISIT_URL,
            TOOL_WEB_SEARCH,
            TOOL_HISTORY_BACK,
            TOOL_CLICK,
            TOOL_TYPE,
            TOOL_READ_PAGE_AND_ANSWER,
            TOOL_SUMMARIZE_PAGE,
            TOOL_SLEEP,
            TOOL_HOVER,
        ]
        self.n_lines_page_text = 50  # Number of lines of text to extract from the page in the absence of OCR
        self.did_lazy_init = False  # flag to check if we have initialized the browser

    async def _lazy_init(
        self,
    ) -> None:
        """
        On the first call, we initialize the browser and the page.
        """
        self._last_download = None
        self._prior_metadata_hash = None

        # Create the playwright self
        launch_args: Dict[str, Any] = {"headless": self.headless}
        if self.browser_channel is not None:
            launch_args["channel"] = self.browser_channel
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        # Create the context -- are we launching persistent?
        if self._context is None:
            if self.browser_data_dir is None:
                browser = await self._playwright.chromium.launch(**launch_args)
                self._context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
                )
            else:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    self.browser_data_dir, **launch_args
                )

        # Create the page
        self._context.set_default_timeout(60000)  # One minute
        self._page = await self._context.new_page()
        assert self._page is not None
        # self._page.route(lambda x: True, self._route_handler)
        self._page.on("download", self._download_handler)
        if self.to_resize_viewport:
            await self._page.set_viewport_size({"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT})
        await self._page.add_init_script(
            path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js")
        )
        await self._page.goto(self.start_page)
        await self._page.wait_for_load_state()

        # Prepare the debug directory -- which stores the screenshots generated throughout the process
        await self._set_debug_dir(self.debug_dir)
        self.did_lazy_init = True

    async def close(self) -> None:
        """
        Close the browser and the page.
        Should be called when the agent is no longer needed.
        """
        if self._page is not None:
            await self._page.close()
            self._page = None
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def _set_debug_dir(self, debug_dir: str | None) -> None:
        assert self._page is not None
        if self.debug_dir is None:
            return

        if not os.path.isdir(self.debug_dir):
            os.mkdir(self.debug_dir)

        if self.to_save_screenshots:
            current_timestamp = "_" + int(time.time()).__str__()
            screenshot_png_name = "screenshot" + current_timestamp + ".png"
            await self._page.screenshot(path=os.path.join(self.debug_dir, screenshot_png_name))
            self.logger.info(
                WebSurferEvent(
                    source=self.name,
                    url=self._page.url,
                    message="Screenshot: " + screenshot_png_name,
                )
            )

    @property
    def produced_message_types(self) -> Tuple[type[ChatMessage], ...]:
        return (MultiModalMessage,)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        if not self.did_lazy_init:
            return
        assert self._page is not None

        self._chat_history.clear()
        reset_prior_metadata, reset_last_download = await self._playwright_controller.visit_page(
            self._page, self.start_page
        )
        if reset_last_download and self._last_download is not None:
            self._last_download = None
        if reset_prior_metadata and self._prior_metadata_hash is not None:
            self._prior_metadata_hash = None
        if self.to_save_screenshots:
            current_timestamp = "_" + int(time.time()).__str__()
            screenshot_png_name = "screenshot" + current_timestamp + ".png"
            await self._page.screenshot(path=os.path.join(self.debug_dir, screenshot_png_name))  # type: ignore
            self.logger.info(
                WebSurferEvent(
                    source=self.name,
                    url=self._page.url,
                    message="Screenshot: " + screenshot_png_name,
                )
            )

        self.logger.info(
            WebSurferEvent(
                source=self.name,
                url=self._page.url,
                message="Resetting browser.",
            )
        )

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        for chat_message in messages:
            if isinstance(chat_message, TextMessage | MultiModalMessage):
                self._chat_history.append(UserMessage(content=chat_message.content, source=chat_message.source))
            else:
                raise ValueError(f"Unexpected message in MultiModalWebSurfer: {chat_message}")
        self.inner_messages: List[AgentEvent | ChatMessage] = []
        self.model_usage: List[RequestUsage] = []
        try:
            content = await self._generate_reply(cancellation_token=cancellation_token)
            self._chat_history.append(AssistantMessage(content=message_content_to_str(content), source=self.name))
            final_usage = RequestUsage(
                prompt_tokens=sum([u.prompt_tokens for u in self.model_usage]),
                completion_tokens=sum([u.completion_tokens for u in self.model_usage]),
            )
            if isinstance(content, str):
                yield Response(
                    chat_message=TextMessage(content=content, source=self.name, models_usage=final_usage),
                    inner_messages=self.inner_messages,
                )
            else:
                yield Response(
                    chat_message=MultiModalMessage(content=content, source=self.name, models_usage=final_usage),
                    inner_messages=self.inner_messages,
                )

        except BaseException:
            content = f"Web surfing error:\n\n{traceback.format_exc()}"
            self._chat_history.append(AssistantMessage(content=content, source=self.name))
            yield Response(chat_message=TextMessage(content=content, source=self.name))

    async def _generate_reply(self, cancellation_token: CancellationToken) -> UserContent:
        """Generates the actual reply. First calls the LLM to figure out which tool to use, then executes the tool."""

        # Lazy init, initialize the browser and the page on the first generate reply only
        if not self.did_lazy_init:
            await self._lazy_init()

        assert self._page is not None

        # Clone the messages to give context, removing old screenshots
        history: List[LLMMessage] = []
        for m in self._chat_history:
            assert isinstance(m, UserMessage | AssistantMessage | SystemMessage)
            assert isinstance(m.content, str | list)

            if isinstance(m.content, str):
                history.append(m)
            else:
                content = message_content_to_str(m.content)
                if isinstance(m, UserMessage):
                    history.append(UserMessage(content=content, source=m.source))
                elif isinstance(m, AssistantMessage):
                    history.append(AssistantMessage(content=content, source=m.source))
                elif isinstance(m, SystemMessage):
                    history.append(SystemMessage(content=content))

        # Ask the page for interactive elements, then prepare the state-of-mark screenshot
        rects = await self._playwright_controller.get_interactive_rects(self._page)
        viewport = await self._playwright_controller.get_visual_viewport(self._page)
        screenshot = await self._page.screenshot()
        som_screenshot, visible_rects, rects_above, rects_below = add_set_of_mark(screenshot, rects)

        if self.to_save_screenshots:
            current_timestamp = "_" + int(time.time()).__str__()
            screenshot_png_name = "screenshot_som" + current_timestamp + ".png"
            som_screenshot.save(os.path.join(self.debug_dir, screenshot_png_name))  # type: ignore
            self.logger.info(
                WebSurferEvent(
                    source=self.name,
                    url=self._page.url,
                    message="Screenshot: " + screenshot_png_name,
                )
            )
        # What tools are available?
        tools = self.default_tools.copy()

        # We can scroll up
        if viewport["pageTop"] > 5:
            tools.append(TOOL_PAGE_UP)

        # Can scroll down
        if (viewport["pageTop"] + viewport["height"] + 5) < viewport["scrollHeight"]:
            tools.append(TOOL_PAGE_DOWN)

        # Focus hint
        focused = await self._playwright_controller.get_focused_rect_id(self._page)
        focused_hint = ""
        if focused:
            name = self._target_name(focused, rects)
            if name:
                name = f"(and name '{name}') "

            role = "control"
            try:
                role = rects[focused]["role"]
            except KeyError:
                pass

            focused_hint = f"\nThe {role} with ID {focused} {name}currently has the input focus.\n\n"

        # Everything visible
        visible_targets = "\n".join(self._format_target_list(visible_rects, rects)) + "\n\n"

        # Everything else
        other_targets: List[str] = []
        other_targets.extend(self._format_target_list(rects_above, rects))
        other_targets.extend(self._format_target_list(rects_below, rects))

        if len(other_targets) > 0:
            other_targets_str = (
                "Additional valid interaction targets (not shown) include:\n" + "\n".join(other_targets) + "\n\n"
            )
        else:
            other_targets_str = ""

        tool_names = "\n".join([t["name"] for t in tools])

        text_prompt = WEB_SURFER_TOOL_PROMPT.format(
            url=self._page.url,
            visible_targets=visible_targets,
            other_targets_str=other_targets_str,
            focused_hint=focused_hint,
            tool_names=tool_names,
        ).strip()

        # Scale the screenshot for the MLM, and close the original
        scaled_screenshot = som_screenshot.resize((self.MLM_WIDTH, self.MLM_HEIGHT))
        som_screenshot.close()
        if self.to_save_screenshots:
            scaled_screenshot.save(os.path.join(self.debug_dir, "screenshot_scaled.png"))  # type: ignore

        # Add the multimodal message and make the request
        history.append(UserMessage(content=[text_prompt, AGImage.from_pil(scaled_screenshot)], source=self.name))

        response = await self._model_client.create(
            history, tools=tools, extra_create_args={"tool_choice": "auto"}, cancellation_token=cancellation_token
        )  # , "parallel_tool_calls": False})
        self.model_usage.append(response.usage)
        message = response.content
        self._last_download = None
        if isinstance(message, str):
            # Answer directly
            self.inner_messages.append(TextMessage(content=message, source=self.name))
            return message
        elif isinstance(message, list):
            # Take an action
            return await self._execute_tool(message, rects, tool_names, cancellation_token=cancellation_token)
        else:
            # Not sure what happened here
            raise AssertionError(f"Unknown response format '{message}'")

    async def _execute_tool(
        self,
        message: List[FunctionCall],
        rects: Dict[str, InteractiveRegion],
        tool_names: str,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> UserContent:
        # Execute the tool
        name = message[0].name
        args = json.loads(message[0].arguments)
        action_description = ""
        assert self._page is not None
        self.logger.info(
            WebSurferEvent(
                source=self.name,
                url=self._page.url,
                action=name,
                arguments=args,
                message=f"{name}( {json.dumps(args)} )",
            )
        )
        self.inner_messages.append(TextMessage(content=f"{name}( {json.dumps(args)} )", source=self.name))

        if name == "visit_url":
            url = args.get("url")
            action_description = f"I typed '{url}' into the browser address bar."
            # Check if the argument starts with a known protocol
            if url.startswith(("https://", "http://", "file://", "about:")):
                reset_prior_metadata, reset_last_download = await self._playwright_controller.visit_page(
                    self._page, url
                )
            # If the argument contains a space, treat it as a search query
            elif " " in url:
                reset_prior_metadata, reset_last_download = await self._playwright_controller.visit_page(
                    self._page, f"https://www.bing.com/search?q={quote_plus(url)}&FORM=QBLH"
                )
            # Otherwise, prefix with https://
            else:
                reset_prior_metadata, reset_last_download = await self._playwright_controller.visit_page(
                    self._page, "https://" + url
                )
            if reset_last_download and self._last_download is not None:
                self._last_download = None
            if reset_prior_metadata and self._prior_metadata_hash is not None:
                self._prior_metadata_hash = None
        elif name == "history_back":
            action_description = "I clicked the browser back button."
            await self._playwright_controller.back(self._page)

        elif name == "web_search":
            query = args.get("query")
            action_description = f"I typed '{query}' into the browser search bar."
            reset_prior_metadata, reset_last_download = await self._playwright_controller.visit_page(
                self._page, f"https://www.bing.com/search?q={quote_plus(query)}&FORM=QBLH"
            )
            if reset_last_download and self._last_download is not None:
                self._last_download = None
            if reset_prior_metadata and self._prior_metadata_hash is not None:
                self._prior_metadata_hash = None
        elif name == "page_up":
            action_description = "I scrolled up one page in the browser."
            await self._playwright_controller.page_up(self._page)
        elif name == "page_down":
            action_description = "I scrolled down one page in the browser."
            await self._playwright_controller.page_down(self._page)

        elif name == "click":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)
            if target_name:
                action_description = f"I clicked '{target_name}'."
            else:
                action_description = "I clicked the control."
            new_page_tentative = await self._playwright_controller.click_id(self._page, target_id)
            if new_page_tentative is not None:
                self._page = new_page_tentative
                self._prior_metadata_hash = None
                self.logger.info(
                    WebSurferEvent(
                        source=self.name,
                        url=self._page.url,
                        message="New tab or window.",
                    )
                )
        elif name == "input_text":
            input_field_id = str(args.get("input_field_id"))
            text_value = str(args.get("text_value"))
            input_field_name = self._target_name(input_field_id, rects)
            if input_field_name:
                action_description = f"I typed '{text_value}' into '{input_field_name}'."
            else:
                action_description = f"I input '{text_value}'."
            await self._playwright_controller.fill_id(self._page, input_field_id, text_value)

        elif name == "scroll_element_up":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)

            if target_name:
                action_description = f"I scrolled '{target_name}' up."
            else:
                action_description = "I scrolled the control up."

            await self._playwright_controller.scroll_id(self._page, target_id, "up")

        elif name == "scroll_element_down":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)

            if target_name:
                action_description = f"I scrolled '{target_name}' down."
            else:
                action_description = "I scrolled the control down."

            await self._playwright_controller.scroll_id(self._page, target_id, "down")

        elif name == "answer_question":
            question = str(args.get("question"))
            action_description = f"I answered the following question '{question}' based on the web page."
            # Do Q&A on the DOM. No need to take further action. Browser state does not change.
            return await self._summarize_page(question=question, cancellation_token=cancellation_token)
        elif name == "summarize_page":
            # Summarize the DOM. No need to take further action. Browser state does not change.
            action_description = "I summarized the current web page"
            return await self._summarize_page(cancellation_token=cancellation_token)

        elif name == "hover":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)
            if target_name:
                action_description = f"I hovered over '{target_name}'."
            else:
                action_description = "I hovered over the control."
            await self._playwright_controller.hover_id(self._page, target_id)

        elif name == "sleep":
            action_description = "I am waiting a short period of time before taking further action."
            await self._playwright_controller.sleep(self._page, 3)

        else:
            raise ValueError(f"Unknown tool '{name}'. Please choose from:\n\n{tool_names}")

        await self._page.wait_for_load_state()
        await self._playwright_controller.sleep(self._page, 3)

        # Handle downloads
        if self._last_download is not None and self.downloads_folder is not None:
            fname = os.path.join(self.downloads_folder, self._last_download.suggested_filename)
            await self._last_download.save_as(fname)  # type: ignore
            page_body = f"<html><head><title>Download Successful</title></head><body style=\"margin: 20px;\"><h1>Successfully downloaded '{self._last_download.suggested_filename}' to local path:<br><br>{fname}</h1></body></html>"
            await self._page.goto(
                "data:text/html;base64," + base64.b64encode(page_body.encode("utf-8")).decode("utf-8")
            )
            await self._page.wait_for_load_state()

        # Handle metadata
        page_metadata = json.dumps(await self._playwright_controller.get_page_metadata(self._page), indent=4)
        metadata_hash = hashlib.md5(page_metadata.encode("utf-8")).hexdigest()
        if metadata_hash != self._prior_metadata_hash:
            page_metadata = (
                "\nThe following metadata was extracted from the webpage:\n\n" + page_metadata.strip() + "\n"
            )
        else:
            page_metadata = ""
        self._prior_metadata_hash = metadata_hash

        # Describe the viewport of the new page in words
        viewport = await self._playwright_controller.get_visual_viewport(self._page)
        percent_visible = int(viewport["height"] * 100 / viewport["scrollHeight"])
        percent_scrolled = int(viewport["pageTop"] * 100 / viewport["scrollHeight"])
        if percent_scrolled < 1:  # Allow some rounding error
            position_text = "at the top of the page"
        elif percent_scrolled + percent_visible >= 99:  # Allow some rounding error
            position_text = "at the bottom of the page"
        else:
            position_text = str(percent_scrolled) + "% down from the top of the page"

        new_screenshot = await self._page.screenshot()
        if self.to_save_screenshots:
            current_timestamp = "_" + int(time.time()).__str__()
            screenshot_png_name = "screenshot" + current_timestamp + ".png"
            async with aiofiles.open(os.path.join(self.debug_dir, screenshot_png_name), "wb") as file:  # type: ignore
                await file.write(new_screenshot)  # type: ignore
            self.logger.info(
                WebSurferEvent(
                    source=self.name,
                    url=self._page.url,
                    message="Screenshot: " + screenshot_png_name,
                )
            )

        ocr_text = (
            await self._get_ocr_text(new_screenshot, cancellation_token=cancellation_token)
            if self.use_ocr is True
            else await self._playwright_controller.get_webpage_text(self._page, n_lines=self.n_lines_page_text)
        )

        # Return the complete observation
        page_title = await self._page.title()
        message_content = f"{action_description}\n\n Here is a screenshot of the webpage: [{page_title}]({self._page.url}).\n The viewport shows {percent_visible}% of the webpage, and is positioned {position_text} {page_metadata}\n"
        if self.use_ocr:
            message_content += f"Automatic OCR of the page screenshot has detected the following text:\n\n{ocr_text}"
        else:
            message_content += f"The first {self.n_lines_page_text} lines of the page text is:\n\n{ocr_text}"

        return [
            message_content,
            AGImage.from_pil(PIL.Image.open(io.BytesIO(new_screenshot))),
        ]

    def _target_name(self, target: str, rects: Dict[str, InteractiveRegion]) -> str | None:
        try:
            return rects[target]["aria_name"].strip()
        except KeyError:
            return None

    def _format_target_list(self, ids: List[str], rects: Dict[str, InteractiveRegion]) -> List[str]:
        """
        Format the list of targets in the webpage as a string to be used in the agent's prompt.
        """
        targets: List[str] = []
        for r in list(set(ids)):
            if r in rects:
                # Get the role
                aria_role = rects[r].get("role", "").strip()
                if len(aria_role) == 0:
                    aria_role = rects[r].get("tag_name", "").strip()

                # Get the name
                aria_name = re.sub(r"[\n\r]+", " ", rects[r].get("aria_name", "")).strip()

                # What are the actions?
                actions = ['"click", "hover"']
                if rects[r]["role"] in ["textbox", "searchbox", "search"]:
                    actions = ['"input_text"']
                actions_str = "[" + ",".join(actions) + "]"

                targets.append(f'{{"id": {r}, "name": "{aria_name}", "role": "{aria_role}", "tools": {actions_str} }}')

        return targets

    async def _get_ocr_text(
        self, image: bytes | io.BufferedIOBase | PIL.Image.Image, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        scaled_screenshot = None
        if isinstance(image, PIL.Image.Image):
            scaled_screenshot = image.resize((self.MLM_WIDTH, self.MLM_HEIGHT))
        else:
            pil_image = None
            if not isinstance(image, io.BufferedIOBase):
                pil_image = PIL.Image.open(io.BytesIO(image))
            else:
                pil_image = PIL.Image.open(cast(BinaryIO, image))
            scaled_screenshot = pil_image.resize((self.MLM_WIDTH, self.MLM_HEIGHT))
            pil_image.close()

        # Add the multimodal message and make the request
        messages: List[LLMMessage] = []
        messages.append(
            UserMessage(
                content=[
                    WEB_SURFER_OCR_PROMPT,
                    AGImage.from_pil(scaled_screenshot),
                ],
                source=self.name,
            )
        )
        response = await self._model_client.create(messages, cancellation_token=cancellation_token)
        self.model_usage.append(response.usage)
        scaled_screenshot.close()
        assert isinstance(response.content, str)
        return response.content

    async def _summarize_page(
        self,
        question: str | None = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> str:
        assert self._page is not None

        page_markdown: str = await self._playwright_controller.get_page_markdown(self._page)

        title: str = self._page.url
        try:
            title = await self._page.title()
        except Exception:
            pass

        # Take a screenshot and scale it
        screenshot = Image.open(io.BytesIO(await self._page.screenshot()))
        scaled_screenshot = screenshot.resize((self.MLM_WIDTH, self.MLM_HEIGHT))
        screenshot.close()
        ag_image = AGImage.from_pil(scaled_screenshot)

        # Prepare the system prompt
        messages: List[LLMMessage] = []
        messages.append(SystemMessage(content=WEB_SURFER_QA_SYSTEM_MESSAGE))
        prompt = WEB_SURFER_QA_PROMPT(title, question)
        # Grow the buffer (which is added to the prompt) until we overflow the context window or run out of lines
        buffer = ""
        # for line in re.split(r"([\r\n]+)", page_markdown):
        for line in page_markdown.splitlines():
            message = UserMessage(
                # content=[
                content=prompt + buffer + line,
                #    ag_image,
                # ],
                source=self.name,
            )

            remaining = self._model_client.remaining_tokens(messages + [message])
            if remaining > self.SCREENSHOT_TOKENS:
                buffer += line
            else:
                break

        # Nothing to do
        buffer = buffer.strip()
        if len(buffer) == 0:
            return "Nothing to summarize."

        # Append the message
        messages.append(
            UserMessage(
                content=[
                    prompt + buffer,
                    ag_image,
                ],
                source=self.name,
            )
        )

        # Generate the response
        response = await self._model_client.create(messages, cancellation_token=cancellation_token)
        self.model_usage.append(response.usage)
        scaled_screenshot.close()
        assert isinstance(response.content, str)
        return response.content
