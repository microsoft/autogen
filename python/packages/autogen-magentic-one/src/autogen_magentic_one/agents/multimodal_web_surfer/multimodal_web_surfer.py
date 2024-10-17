import base64
import hashlib
import io
import json
import logging
import os
import pathlib
import re
import traceback
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union, cast  # Any, Callable, Dict, List, Literal, Tuple
from urllib.parse import quote_plus  # parse_qs, quote, unquote, urlparse, urlunparse

import aiofiles
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall, default_subscription
from autogen_core.components import Image as AGImage
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from PIL import Image
from playwright._impl._errors import Error as PlaywrightError
from playwright._impl._errors import TimeoutError

# from playwright._impl._async_base.AsyncEventInfo
from playwright.async_api import BrowserContext, Download, Page, Playwright, async_playwright

# TODO: Fix mdconvert
from ...markdown_browser import MarkdownConverter  # type: ignore
from ...messages import UserContent, WebSurferEvent
from ...utils import SentinelMeta, message_content_to_str
from ..base_worker import BaseWorker
from .set_of_mark import add_set_of_mark
from .tool_definitions import (
    TOOL_CLICK,
    TOOL_HISTORY_BACK,
    TOOL_PAGE_DOWN,
    TOOL_PAGE_UP,
    TOOL_READ_PAGE_AND_ANSWER,
    # TOOL_SCROLL_ELEMENT_DOWN,
    # TOOL_SCROLL_ELEMENT_UP,
    TOOL_SLEEP,
    TOOL_SUMMARIZE_PAGE,
    TOOL_TYPE,
    TOOL_VISIT_URL,
    TOOL_WEB_SEARCH,
)
from .types import (
    InteractiveRegion,
    VisualViewport,
    interactiveregion_from_dict,
    visualviewport_from_dict,
)

# Viewport dimensions
VIEWPORT_HEIGHT = 900
VIEWPORT_WIDTH = 1440

# Size of the image we send to the MLM
# Current values represent a 0.85 scaling to fit within the GPT-4v short-edge constraints (768px)
MLM_HEIGHT = 765
MLM_WIDTH = 1224

SCREENSHOT_TOKENS = 1105


# Sentinels
class DEFAULT_CHANNEL(metaclass=SentinelMeta):
    pass


@default_subscription
class MultimodalWebSurfer(BaseWorker):
    """(In preview) A multimodal agent that acts as a web surfer that can search the web and visit web pages."""

    DEFAULT_DESCRIPTION = "A helpful assistant with access to a web browser. Ask them to perform web searches, open pages, and interact with content (e.g., clicking links, scrolling the viewport, etc., filling in form fields, etc.) It can also summarize the entire page, or answer questions based on the content of the page. It can also be asked to sleep and wait for pages to load, in cases where the pages seem to be taking a while to load."

    DEFAULT_START_PAGE = "https://www.bing.com/"

    def __init__(
        self,
        description: str = DEFAULT_DESCRIPTION,
    ):
        """Do not instantiate directly. Call MultimodalWebSurfer.create instead."""
        super().__init__(description)

        # Call init to set these
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._last_download: Download | None = None
        self._prior_metadata_hash: str | None = None
        self.logger = logging.getLogger(EVENT_LOGGER_NAME + f".{self.id.key}.MultimodalWebSurfer")

        # Read page_script
        self._page_script: str = ""
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
            self._page_script = fh.read()

        # Define the download handler
        def _download_handler(download: Download) -> None:
            self._last_download = download

        self._download_handler = _download_handler

    async def init(
        self,
        model_client: ChatCompletionClient,
        headless: bool = True,
        browser_channel: str | type[DEFAULT_CHANNEL] = DEFAULT_CHANNEL,
        browser_data_dir: str | None = None,
        start_page: str | None = None,
        downloads_folder: str | None = None,
        debug_dir: str | None = os.getcwd(),
        # navigation_allow_list=lambda url: True,
        markdown_converter: Any | None = None,  # TODO: Fixme
    ) -> None:
        self._model_client = model_client
        self.start_page = start_page or self.DEFAULT_START_PAGE
        self.downloads_folder = downloads_folder
        self._chat_history: List[LLMMessage] = []
        self._last_download = None
        self._prior_metadata_hash = None

        ## Create or use the provided MarkdownConverter
        if markdown_converter is None:
            self._markdown_converter = MarkdownConverter()  # type: ignore
        else:
            self._markdown_converter = markdown_converter  # type: ignore

        # Create the playwright self
        launch_args: Dict[str, Any] = {"headless": headless}
        if browser_channel is not DEFAULT_CHANNEL:
            launch_args["channel"] = browser_channel
        self._playwright = await async_playwright().start()

        # Create the context -- are we launching persistent?
        if browser_data_dir is None:
            browser = await self._playwright.chromium.launch(**launch_args)
            self._context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
            )
        else:
            self._context = await self._playwright.chromium.launch_persistent_context(browser_data_dir, **launch_args)

        # Create the page
        self._context.set_default_timeout(60000)  # One minute
        self._page = await self._context.new_page()
        assert self._page is not None
        # self._page.route(lambda x: True, self._route_handler)
        self._page.on("download", self._download_handler)
        await self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        await self._page.add_init_script(
            path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js")
        )
        await self._page.goto(self.start_page)
        await self._page.wait_for_load_state()

        # Prepare the debug directory -- which stores the screenshots generated throughout the process
        await self._set_debug_dir(debug_dir)

    async def _sleep(self, duration: Union[int, float]) -> None:
        assert self._page is not None
        await self._page.wait_for_timeout(duration * 1000)

    async def _set_debug_dir(self, debug_dir: str | None) -> None:
        assert self._page is not None
        self.debug_dir = debug_dir
        if self.debug_dir is None:
            return

        if not os.path.isdir(self.debug_dir):
            os.mkdir(self.debug_dir)

        debug_html = os.path.join(self.debug_dir, "screenshot.html")
        async with aiofiles.open(debug_html, "wt") as file:
            await file.write(
                f"""
<html style="width:100%; margin: 0px; padding: 0px;">
<body style="width: 100%; margin: 0px; padding: 0px;">
    <img src="screenshot.png" id="main_image" style="width: 100%; max-width: {VIEWPORT_WIDTH}px; margin: 0px; padding: 0px;">
    <script language="JavaScript">
var counter = 0;
setInterval(function() {{
   counter += 1;
   document.getElementById("main_image").src = "screenshot.png?bc=" + counter;
}}, 300);
    </script>
</body>
</html>
""".strip(),
            )
        await self._page.screenshot(path=os.path.join(self.debug_dir, "screenshot.png"))
        self.logger.info(f"Multimodal Web Surfer debug screens: {pathlib.Path(os.path.abspath(debug_html)).as_uri()}\n")

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        assert self._page is not None
        future = super()._reset(cancellation_token)
        await future
        await self._visit_page(self.start_page)
        if self.debug_dir:
            await self._page.screenshot(path=os.path.join(self.debug_dir, "screenshot.png"))
        self.logger.info(
            WebSurferEvent(
                source=self.metadata["type"],
                url=self._page.url,
                message="Resetting browser.",
            )
        )

    def _target_name(self, target: str, rects: Dict[str, InteractiveRegion]) -> str | None:
        try:
            return rects[target]["aria_name"].strip()
        except KeyError:
            return None

    def _format_target_list(self, ids: List[str], rects: Dict[str, InteractiveRegion]) -> List[str]:
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
                actions = ['"click"']
                if rects[r]["role"] in ["textbox", "searchbox", "search"]:
                    actions = ['"input_text"']
                actions_str = "[" + ",".join(actions) + "]"

                targets.append(f'{{"id": {r}, "name": "{aria_name}", "role": "{aria_role}", "tools": {actions_str} }}')

        return targets

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        assert self._page is not None
        try:
            request_halt, content = await self.__generate_reply(cancellation_token)
            return request_halt, content
        except Exception:
            return False, f"Web surfing error:\n\n{traceback.format_exc()}"

    async def _execute_tool(
        self,
        message: List[FunctionCall],
        rects: Dict[str, InteractiveRegion],
        tool_names: str,
        use_ocr: bool = True,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Tuple[bool, UserContent]:
        name = message[0].name
        args = json.loads(message[0].arguments)
        action_description = ""
        assert self._page is not None
        self.logger.info(
            WebSurferEvent(
                source=self.metadata["type"],
                url=self._page.url,
                action=name,
                arguments=args,
                message=f"{name}( {json.dumps(args)} )",
            )
        )

        if name == "visit_url":
            url = args.get("url")
            action_description = f"I typed '{url}' into the browser address bar."
            # Check if the argument starts with a known protocol
            if url.startswith(("https://", "http://", "file://", "about:")):
                await self._visit_page(url)
            # If the argument contains a space, treat it as a search query
            elif " " in url:
                await self._visit_page(f"https://www.bing.com/search?q={quote_plus(url)}&FORM=QBLH")
            # Otherwise, prefix with https://
            else:
                await self._visit_page("https://" + url)

        elif name == "history_back":
            action_description = "I clicked the browser back button."
            await self._back()

        elif name == "web_search":
            query = args.get("query")
            action_description = f"I typed '{query}' into the browser search bar."
            await self._visit_page(f"https://www.bing.com/search?q={quote_plus(query)}&FORM=QBLH")

        elif name == "page_up":
            action_description = "I scrolled up one page in the browser."
            await self._page_up()

        elif name == "page_down":
            action_description = "I scrolled down one page in the browser."
            await self._page_down()

        elif name == "click":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)
            if target_name:
                action_description = f"I clicked '{target_name}'."
            else:
                action_description = "I clicked the control."
            await self._click_id(target_id)

        elif name == "input_text":
            input_field_id = str(args.get("input_field_id"))
            text_value = str(args.get("text_value"))
            input_field_name = self._target_name(input_field_id, rects)
            if input_field_name:
                action_description = f"I typed '{text_value}' into '{input_field_name}'."
            else:
                action_description = f"I input '{text_value}'."
            await self._fill_id(input_field_id, text_value)

        elif name == "scroll_element_up":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)

            if target_name:
                action_description = f"I scrolled '{target_name}' up."
            else:
                action_description = "I scrolled the control up."

            await self._scroll_id(target_id, "up")

        elif name == "scroll_element_down":
            target_id = str(args.get("target_id"))
            target_name = self._target_name(target_id, rects)

            if target_name:
                action_description = f"I scrolled '{target_name}' down."
            else:
                action_description = "I scrolled the control down."

            await self._scroll_id(target_id, "down")

        elif name == "answer_question":
            question = str(args.get("question"))
            # Do Q&A on the DOM. No need to take further action. Browser state does not change.
            return False, await self._summarize_page(question=question, cancellation_token=cancellation_token)

        elif name == "summarize_page":
            # Summarize the DOM. No need to take further action. Browser state does not change.
            return False, await self._summarize_page(cancellation_token=cancellation_token)

        elif name == "sleep":
            action_description = "I am waiting a short period of time before taking further action."
            await self._sleep(3)  # There's a 2s sleep below too

        else:
            raise ValueError(f"Unknown tool '{name}'. Please choose from:\n\n{tool_names}")

        await self._page.wait_for_load_state()
        await self._sleep(3)

        # Handle downloads
        if self._last_download is not None and self.downloads_folder is not None:
            fname = os.path.join(self.downloads_folder, self._last_download.suggested_filename)
            # TODO: Fix this type
            await self._last_download.save_as(fname)  # type: ignore
            page_body = f"<html><head><title>Download Successful</title></head><body style=\"margin: 20px;\"><h1>Successfully downloaded '{self._last_download.suggested_filename}' to local path:<br><br>{fname}</h1></body></html>"
            await self._page.goto(
                "data:text/html;base64," + base64.b64encode(page_body.encode("utf-8")).decode("utf-8")
            )
            await self._page.wait_for_load_state()

        # Handle metadata
        page_metadata = json.dumps(await self._get_page_metadata(), indent=4)
        metadata_hash = hashlib.sha256(page_metadata.encode("utf-8")).hexdigest()
        if metadata_hash != self._prior_metadata_hash:
            page_metadata = (
                "\nThe following metadata was extracted from the webpage:\n\n" + page_metadata.strip() + "\n"
            )
        else:
            page_metadata = ""
        self._prior_metadata_hash = metadata_hash

        # Describe the viewport of the new page in words
        viewport = await self._get_visual_viewport()
        percent_visible = int(viewport["height"] * 100 / viewport["scrollHeight"])
        percent_scrolled = int(viewport["pageTop"] * 100 / viewport["scrollHeight"])
        if percent_scrolled < 1:  # Allow some rounding error
            position_text = "at the top of the page"
        elif percent_scrolled + percent_visible >= 99:  # Allow some rounding error
            position_text = "at the bottom of the page"
        else:
            position_text = str(percent_scrolled) + "% down from the top of the page"

        new_screenshot = await self._page.screenshot()
        if self.debug_dir:
            async with aiofiles.open(os.path.join(self.debug_dir, "screenshot.png"), "wb") as file:
                await file.write(new_screenshot)

        ocr_text = (
            await self._get_ocr_text(new_screenshot, cancellation_token=cancellation_token) if use_ocr is True else ""
        )

        # Return the complete observation
        message_content = ""  # message.content or ""
        page_title = await self._page.title()

        return False, [
            f"{message_content}\n\n{action_description}\n\nHere is a screenshot of [{page_title}]({self._page.url}). The viewport shows {percent_visible}% of the webpage, and is positioned {position_text}.{page_metadata}\nAutomatic OCR of the page screenshot has detected the following text:\n\n{ocr_text}".strip(),
            AGImage.from_pil(Image.open(io.BytesIO(new_screenshot))),
        ]

    async def __generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        assert self._page is not None
        """Generates the actual reply. First calls the LLM to figure out which tool to use, then executes the tool."""

        # Clone the messages to give context, removing old screenshots
        history: List[LLMMessage] = []
        for m in self._chat_history:
            if isinstance(m.content, str):
                history.append(m)
            elif isinstance(m.content, list):
                content = message_content_to_str(m.content)
                if isinstance(m, UserMessage):
                    history.append(UserMessage(content=content, source=m.source))
                elif isinstance(m, AssistantMessage):
                    history.append(AssistantMessage(content=content, source=m.source))
                elif isinstance(m, SystemMessage):
                    history.append(SystemMessage(content=content))

        # Ask the page for interactive elements, then prepare the state-of-mark screenshot
        rects = await self._get_interactive_rects()
        viewport = await self._get_visual_viewport()
        screenshot = await self._page.screenshot()
        som_screenshot, visible_rects, rects_above, rects_below = add_set_of_mark(screenshot, rects)

        if self.debug_dir:
            som_screenshot.save(os.path.join(self.debug_dir, "screenshot.png"))

        # What tools are available?
        tools = [
            TOOL_VISIT_URL,
            TOOL_HISTORY_BACK,
            TOOL_CLICK,
            TOOL_TYPE,
            TOOL_SUMMARIZE_PAGE,
            TOOL_READ_PAGE_AND_ANSWER,
            TOOL_SLEEP,
        ]

        # Can we reach Bing to search?
        # if self._navigation_allow_list("https://www.bing.com/"):
        tools.append(TOOL_WEB_SEARCH)

        # We can scroll up
        if viewport["pageTop"] > 5:
            tools.append(TOOL_PAGE_UP)

        # Can scroll down
        if (viewport["pageTop"] + viewport["height"] + 5) < viewport["scrollHeight"]:
            tools.append(TOOL_PAGE_DOWN)

        # Focus hint
        focused = await self._get_focused_rect_id()
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

        # If there are scrollable elements, then add the corresponding tools
        # has_scrollable_elements = False
        # if has_scrollable_elements:
        #    tools.append(TOOL_SCROLL_ELEMENT_UP)
        #    tools.append(TOOL_SCROLL_ELEMENT_DOWN)

        tool_names = "\n".join([t["name"] for t in tools])

        text_prompt = f"""
Consider the following screenshot of a web browser, which is open to the page '{self._page.url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

{visible_targets}{other_targets_str}{focused_hint}You are to respond to the user's most recent request by selecting an appropriate tool the following set, or by answering the question directly if possible:

{tool_names}

When deciding between tools, consider if the request can be best addressed by:
    - the contents of the current viewport (in which case actions like clicking links, clicking buttons, or inputting text might be most appropriate)
    - contents found elsewhere on the full webpage (in which case actions like scrolling, summarization, or full-page Q&A might be most appropriate)
    - on some other website entirely (in which case actions like performing a new web search might be the best option)
""".strip()

        # Scale the screenshot for the MLM, and close the original
        scaled_screenshot = som_screenshot.resize((MLM_WIDTH, MLM_HEIGHT))
        som_screenshot.close()
        if self.debug_dir:
            scaled_screenshot.save(os.path.join(self.debug_dir, "screenshot_scaled.png"))

        # Add the multimodal message and make the request
        history.append(
            UserMessage(content=[text_prompt, AGImage.from_pil(scaled_screenshot)], source=self.metadata["type"])
        )
        response = await self._model_client.create(
            history, tools=tools, extra_create_args={"tool_choice": "auto"}, cancellation_token=cancellation_token
        )  # , "parallel_tool_calls": False})
        message = response.content

        self._last_download = None

        if isinstance(message, str):
            # Answer directly
            return False, message
        elif isinstance(message, list):
            # Take an action
            return await self._execute_tool(message, rects, tool_names, cancellation_token=cancellation_token)
        else:
            # Not sure what happened here
            raise AssertionError(f"Unknown response format '{message}'")

    async def _get_interactive_rects(self) -> Dict[str, InteractiveRegion]:
        assert self._page is not None

        # Read the regions from the DOM
        try:
            await self._page.evaluate(self._page_script)
        except Exception:
            pass
        result = cast(
            Dict[str, Dict[str, Any]], await self._page.evaluate("MultimodalWebSurfer.getInteractiveRects();")
        )

        # Convert the results into appropriate types
        assert isinstance(result, dict)
        typed_results: Dict[str, InteractiveRegion] = {}
        for k in result:
            assert isinstance(k, str)
            typed_results[k] = interactiveregion_from_dict(result[k])

        return typed_results

    async def _get_visual_viewport(self) -> VisualViewport:
        assert self._page is not None
        try:
            await self._page.evaluate(self._page_script)
        except Exception:
            pass
        return visualviewport_from_dict(await self._page.evaluate("MultimodalWebSurfer.getVisualViewport();"))

    async def _get_focused_rect_id(self) -> str:
        assert self._page is not None
        try:
            await self._page.evaluate(self._page_script)
        except Exception:
            pass
        result = await self._page.evaluate("MultimodalWebSurfer.getFocusedElementId();")
        return str(result)

    async def _get_page_metadata(self) -> Dict[str, Any]:
        assert self._page is not None
        try:
            await self._page.evaluate(self._page_script)
        except Exception:
            pass
        result = await self._page.evaluate("MultimodalWebSurfer.getPageMetadata();")
        assert isinstance(result, dict)
        return cast(Dict[str, Any], result)

    async def _get_page_markdown(self) -> str:
        assert self._page is not None
        html = await self._page.evaluate("document.documentElement.outerHTML;")
        # TODO: fix types
        res = self._markdown_converter.convert_stream(io.StringIO(html), file_extension=".html", url=self._page.url)  # type: ignore
        return res.text_content  # type: ignore

    async def _on_new_page(self, page: Page) -> None:
        self._page = page
        assert self._page is not None
        # self._page.route(lambda x: True, self._route_handler)
        self._page.on("download", self._download_handler)
        await self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        await self._sleep(0.2)
        self._prior_metadata_hash = None
        await self._page.add_init_script(
            path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js")
        )
        await self._page.wait_for_load_state()

    async def _back(self) -> None:
        assert self._page is not None
        await self._page.go_back()

    async def _visit_page(self, url: str) -> None:
        assert self._page is not None
        try:
            # Regular webpage
            await self._page.goto(url)
            await self._page.wait_for_load_state()
            self._prior_metadata_hash = None
        except Exception as e_outer:
            # Downloaded file
            if self.downloads_folder and "net::ERR_ABORTED" in str(e_outer):
                async with self._page.expect_download() as download_info:
                    try:
                        await self._page.goto(url)
                    except Exception as e_inner:
                        if "net::ERR_ABORTED" in str(e_inner):
                            pass
                        else:
                            raise e_inner
                    download = await download_info.value
                    fname = os.path.join(self.downloads_folder, download.suggested_filename)
                    await download.save_as(fname)
                    message = f"<body style=\"margin: 20px;\"><h1>Successfully downloaded '{download.suggested_filename}' to local path:<br><br>{fname}</h1></body>"
                    await self._page.goto(
                        "data:text/html;base64," + base64.b64encode(message.encode("utf-8")).decode("utf-8")
                    )
                    self._last_download = None  # Since we already handled it
            else:
                raise e_outer

    async def _page_down(self) -> None:
        assert self._page is not None
        await self._page.evaluate(f"window.scrollBy(0, {VIEWPORT_HEIGHT-50});")

    async def _page_up(self) -> None:
        assert self._page is not None
        await self._page.evaluate(f"window.scrollBy(0, -{VIEWPORT_HEIGHT-50});")

    async def _click_id(self, identifier: str) -> None:
        assert self._page is not None
        target = self._page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=100)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Click it
        await target.scroll_into_view_if_needed()
        box = cast(Dict[str, Union[int, float]], await target.bounding_box())
        try:
            # Give it a chance to open a new page
            # TODO: Having trouble with these types
            async with self._page.expect_event("popup", timeout=1000) as page_info:  # type: ignore
                await self._page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, delay=10)
                # If we got this far without error, than a popup or new tab opened. Handle it.

                new_page = await page_info.value  # type: ignore

                assert isinstance(new_page, Page)
                await self._on_new_page(new_page)

                self.logger.info(
                    WebSurferEvent(
                        source=self.metadata["type"],
                        url=self._page.url,
                        message="New tab or window.",
                    )
                )

        except TimeoutError:
            pass

    async def _fill_id(self, identifier: str, value: str) -> None:
        assert self._page is not None
        target = self._page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=100)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Fill it
        await target.scroll_into_view_if_needed()
        await target.focus()
        try:
            await target.fill(value)
        except PlaywrightError:
            await target.press_sequentially(value)
        await target.press("Enter")

    async def _scroll_id(self, identifier: str, direction: str) -> None:
        assert self._page is not None
        await self._page.evaluate(
            f"""
        (function() {{
            let elm = document.querySelector("[__elementId='{identifier}']");
            if (elm) {{
                if ("{direction}" == "up") {{
                    elm.scrollTop = Math.max(0, elm.scrollTop - elm.clientHeight);
                }}
                else {{
                    elm.scrollTop = Math.min(elm.scrollHeight - elm.clientHeight, elm.scrollTop + elm.clientHeight);
                }}
            }}
        }})();
    """
        )

    async def _summarize_page(
        self,
        question: str | None = None,
        token_limit: int = 100000,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> str:
        assert self._page is not None

        page_markdown: str = await self._get_page_markdown()

        title: str = self._page.url
        try:
            title = await self._page.title()
        except Exception:
            pass

        # Take a screenshot and scale it
        screenshot = Image.open(io.BytesIO(await self._page.screenshot()))
        scaled_screenshot = screenshot.resize((MLM_WIDTH, MLM_HEIGHT))
        screenshot.close()
        ag_image = AGImage.from_pil(scaled_screenshot)

        # Prepare the system prompt
        messages: List[LLMMessage] = []
        messages.append(
            SystemMessage(content="You are a helpful assistant that can summarize long documents to answer question.")
        )

        # Prepare the main prompt
        prompt = f"We are visiting the webpage '{title}'. Its full-text content are pasted below, along with a screenshot of the page's current viewport."
        if question is not None:
            prompt += f" Please summarize the webpage into one or two paragraphs with respect to '{question}':\n\n"
        else:
            prompt += " Please summarize the webpage into one or two paragraphs:\n\n"

        # Grow the buffer (which is added to the prompt) until we overflow the context window or run out of lines
        buffer = ""
        for line in re.split(r"([\r\n]+)", page_markdown):
            message = UserMessage(
                # content=[
                prompt + buffer + line,
                #    ag_image,
                # ],
                source=self.metadata["type"],
            )

            remaining = self._model_client.remaining_tokens(messages + [message])
            if remaining > SCREENSHOT_TOKENS:
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
                source=self.metadata["type"],
            )
        )

        # Generate the response
        response = await self._model_client.create(messages, cancellation_token=cancellation_token)
        scaled_screenshot.close()
        assert isinstance(response.content, str)
        return response.content

    async def _get_ocr_text(
        self, image: bytes | io.BufferedIOBase | Image.Image, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        scaled_screenshot = None
        if isinstance(image, Image.Image):
            scaled_screenshot = image.resize((MLM_WIDTH, MLM_HEIGHT))
        else:
            pil_image = None
            if not isinstance(image, io.BufferedIOBase):
                pil_image = Image.open(io.BytesIO(image))
            else:
                # TODO: Not sure why this cast was needed, but by this point screenshot is a binary file-like object
                pil_image = Image.open(cast(BinaryIO, image))
            scaled_screenshot = pil_image.resize((MLM_WIDTH, MLM_HEIGHT))
            pil_image.close()

        # Add the multimodal message and make the request
        messages: List[LLMMessage] = []
        messages.append(
            UserMessage(
                content=[
                    "Please transcribe all visible text on this page, including both main content and the labels of UI elements.",
                    AGImage.from_pil(scaled_screenshot),
                ],
                source=self.metadata["type"],
            )
        )
        response = await self._model_client.create(messages, cancellation_token=cancellation_token)
        scaled_screenshot.close()
        assert isinstance(response.content, str)
        return response.content
