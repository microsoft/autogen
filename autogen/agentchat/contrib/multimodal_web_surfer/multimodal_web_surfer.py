# ruff: noqa: E722
import re
import time
import os
import json
import io
import base64
import pathlib
import hashlib
import traceback
#import numpy as np
#import easyocr
from PIL import Image
from urllib.parse import urlparse, quote, quote_plus, unquote, urlunparse, parse_qs
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple
from typing_extensions import Annotated
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from playwright._impl._errors import Error as PlaywrightError
from .... import Agent, ConversableAgent, OpenAIWrapper
from ....runtime_logging import logging_enabled, log_event
from ....code_utils import content_str
from ....browser_utils.mdconvert import MarkdownConverter, UnsupportedFormatException, FileConversionException
from ....token_count_utils import count_token, get_max_token_limit
from .set_of_mark import add_set_of_mark
from .tool_definitions import (
    TOOL_VISIT_URL,
    TOOL_WEB_SEARCH,
    TOOL_HISTORY_BACK,
    TOOL_PAGE_UP,
    TOOL_PAGE_DOWN,
    TOOL_CLICK,
    TOOL_TYPE,
    TOOL_SCROLL_ELEMENT_DOWN,
    TOOL_SCROLL_ELEMENT_UP,
    TOOL_SUMMARIZE_PAGE,
    TOOL_READ_PAGE_AND_ANSWER,
    TOOL_SLEEP,
)

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


# Sentinels for constructor
DEFAULT_CHANNEL = object()

# Viewport dimensions
VIEWPORT_HEIGHT = 900
VIEWPORT_WIDTH = 1440

# Size of the image we send to the MLM
# Current values represent a 0.85 scaling to fit within the GPT-4v short-edge constraints (768px)
MLM_HEIGHT = 765
MLM_WIDTH = 1224


class MultimodalWebSurferAgent(ConversableAgent):
    """(In preview) A multimodal agent that acts as a web surfer that can search the web and visit web pages."""

    DEFAULT_DESCRIPTION = "A helpful assistant with access to a web browser. Ask them to perform web searches, open pages, and interact with content (e.g., clicking links, scrolling the viewport, etc., filling in form fields, etc.) It can also summarize the entire page, or answer questions based on the content of the page. It can also be asked to sleep and wait for pages to load, in cases where the pages seem to be taking a while to load."

    DEFAULT_START_PAGE = "https://www.bing.com/"

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = None,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        # Browser-related stuff
        headless: bool = True,
        browser_channel=DEFAULT_CHANNEL,
        browser_data_dir: Optional[str] = None,
        start_page: Optional[str] = None,
        downloads_folder: Optional[Union[str, None]] = None,
        debug_dir: Optional[str] = None,
        navigation_allow_list=lambda url: True,
        markdown_converter: Optional[Union[MarkdownConverter, None]] = None,
    ):
        """
        Create a new MultimodalWebSurferAgent.

        Args:
            name: The name of the agent.
            system_message: system message prompt.
            description: The description of the agent.
            is_termination_msg: A function that determines if a received message is a termination message.
            max_consecutive_auto_reply: The maximum number of consecutive auto-replies the agent can make.
            human_input_mode: The mode for human input.
            function_map: A dictionary of functions to register.
            code_execution_config: The configuration for code execution.
            llm_config: The configuration for the LLM.
            default_auto_reply: The default auto-reply.
            headless: Whether to run the browser in headless mode.
            browser_channel: The Chromium channel to use.
            browser_data_dir: The Chromium data directory. If None, a new context is created.
            start_page: The start page for the browser.
            debug_dir: The directory to store debug information. TODO: Clarify behavior on None.
        """
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self.start_page = start_page or self.DEFAULT_START_PAGE
        self.debug_dir = debug_dir or os.getcwd()
        self.downloads_folder = downloads_folder

        #self._ocr_reader = easyocr.Reader(["en"])

        # Handle the allow list
        self._navigation_allow_list = navigation_allow_list
        if isinstance(self._navigation_allow_list, list):

            def _closure(url):
                for entry in navigation_allow_list:
                    if url.startswith(entry):
                        return True
                return False

            self._navigation_allow_list = _closure

        # Configure the router
        def _route_handler(route):
            if route.request.url == "about:blank" or self._navigation_allow_list(route.request.url):
                route.continue_()
            else:
                response = route.fetch()
                if "html" in response.headers.get("content-type", "").lower():
                    route.fulfill(
                        status=403,
                        content_type="text/html",
                        body='<html><body><h1>Navigation Blocked</h1><p>Navigation was blocked by the client. Click the <a href="javascript: history.back()">browser back button</a> to go back, return Home to <a href="'
                        + self.start_page
                        + '">'
                        + self.start_page
                        + "</a>.</p></body></html>",
                    )
                else:
                    route.fulfill(response=response)

        self._route_handler = _route_handler

        # Download handler
        def _download_handler(download):
            self._last_download = download

        self._download_handler = _download_handler
        self._last_download = None
        self._prior_metadata_hash = None

        # Create or use the provided MarkdownConverter
        if markdown_converter is None:
            self._markdown_converter = MarkdownConverter()
        else:
            self._markdown_converter = markdown_converter

        # Create the playwright instance
        launch_args = {"headless": headless}
        if browser_channel is not DEFAULT_CHANNEL:
            launch_args["channel"] = browser_channel
        self._playwright = sync_playwright().start()

        # Create the context -- are we launching a persistent instance?
        if browser_data_dir is None:
            if browser_channel == "chromium":
                browser = self._playwright.chromium.launch(**launch_args)
            elif browser_channel == "firefox":
                browser = self._playwright.firefox.launch(**launch_args)
            else:
                raise NotImplementedError(
                    f"Invalid chromium channel {browser_channel}. Only chromium and firefox are supported."
                )
            self._context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
            )
        else:
            if browser_channel == "chromium":
                self._context = self._playwright.chromium.launch_persistent_context(browser_data_dir, **launch_args)
            elif browser_channel == "firefox":
                self._context = self._playwright.firefox.launch_persistent_context(browser_data_dir, **launch_args)

        # Create the page
        self._context.set_default_timeout(60000) # One minute
        self._page = self._context.new_page()
        self._page.route(lambda x: True, self._route_handler)
        self._page.on("download", self._download_handler)
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.goto(self.start_page)
        self._page.wait_for_load_state()
        self._sleep(1)

        def log_request(source: Agent, request: Any):
            try:
                # getting post_data_json sometimes throws parsing errors
                log_event(
                    source,
                    "mws_request",
                    method=request.method,
                    url=request.url,
                    request_headers=request.all_headers(),
                    request_content=request.post_data_json,
                )
            except Exception as e:
                import traceback

                exc_type = type(e).__name__
                exc_message = str(e)
                exc_traceback = traceback.format_exc().splitlines()
                log_event(
                    source,
                    "exception_thrown_lambda",
                    exc_type=exc_type,
                    exc_message=exc_message,
                    exc_traceback=exc_traceback,
                )
                log_event(
                    source, "mws_request", method=request.method, url=request.url, request_headers=request.all_headers()
                )

        self._page.on("request", lambda request: log_request(self, request) if logging_enabled() else None)
        self._page.on(
            "response",
            lambda response: (
                log_event(
                    self,
                    "mws_response",
                    status=response.status,
                    url=response.url,
                    response_headers=response.all_headers(),
                )
                if logging_enabled()
                else None
            ),
        )

        # Prepare the debug directory -- which stores the screenshots generated throughout the process
        if self.debug_dir:
            if not os.path.isdir(self.debug_dir):
                os.mkdir(self.debug_dir)
            debug_html = os.path.join(self.debug_dir, "screenshot.html")
            with open(debug_html, "wt") as fh:
                fh.write(
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
""".strip()
                )
            self._page.screenshot(path=os.path.join(self.debug_dir, "screenshot.png"))
            print(f"Multimodal Web Surfer debug screens: {pathlib.Path(os.path.abspath(debug_html)).as_uri()}\n")

        self._reply_func_list = []
        self.register_reply([Agent, None], MultimodalWebSurferAgent.generate_surfer_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def reset(self):
        super().reset()
        self._log_to_console(fname="reset", args={"home": self.start_page})
        self._visit_page(self.start_page)
        self._page.wait_for_load_state()
        if self.debug_dir:
            screenshot = self._page.screenshot()
            with open(os.path.join(self.debug_dir, "screenshot.png"), "wb") as png:
                png.write(screenshot)

    def _target_name(self, target, rects):
        target_name = rects.get(str(target), {}).get("aria-name")
        if target_name:
            return target_name.strip()
        else:
            return None

    def _format_target_list(self, ids, rects):
        targets = []
        for r in list(set(ids)):
            if r in rects:
                
                # Get the role
                aria_role = rects[r].get("role", "").strip()
                if len(aria_role) == 0:
                    aria_role = rects[r].get("tag_name", "").strip()
                    
                # Get the name
                aria_name = rects[r].get("aria-name", "").strip()

                # What are the actions?
                actions = ['"click"']
                if rects[r]["role"] in ["textbox", "searchbox", "search"]:
                    actions = ['"input_text"']
                actions = "[" + ",".join(actions) + "]"

                targets.append(f'{{"id": {r}, "name": "{aria_name}", "role": "{aria_role}", "tools": {actions} }}')

        return targets


    def _sleep(self, duration):
        self._page.wait_for_timeout(duration * 1000)


    def generate_surfer_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        try:
            return self._generate_surfer_reply(messages, sender, config)
        except Exception as e:
            if logging_enabled():
                log_event(self, "MultimodalWebSurerError", error=str(e))
            return True, "Web surfing error:\n\n" + str(e)


    def _generate_surfer_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        # Clone the messages to give context, removing old screenshots
        history = []
        for m in messages:
            message = {}
            message.update(m)
            message["content"] = content_str(message["content"])
            history.append(message)

        # Ask the page for interactive elements, then prepare the state-of-mark screenshot
        rects = self._get_interactive_rects()
        viewport = self._get_visual_viewport()
        som_screenshot, visible_rects, rects_above, rects_below = add_set_of_mark(self._page.screenshot(), rects)

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
        if self._navigation_allow_list("https://www.bing.com/"):
            tools.append(TOOL_WEB_SEARCH)

        # We can scroll up
        if viewport["pageTop"] > 5:
            tools.append(TOOL_PAGE_UP)

        # Can scroll down
        if (viewport["pageTop"] + viewport["height"] + 5) < viewport["scrollHeight"]:
            tools.append(TOOL_PAGE_DOWN)

        # Focus hint
        focused = self._get_focused_rect_id()
        focused_hint = ""
        if focused:
            name = rects.get(focused, {}).get("aria-name", "")
            if name:
                name = f"(and name '{name}') "
            focused_hint = (
                "\nThe "
                + rects.get(focused, {}).get("role", "control")
                + " with ID "
                + focused
                + " "
                + name
                + "currently has the input focus.\n\n"
            )

        # Everything visible
        visible_targets = "\n".join(self._format_target_list(visible_rects, rects)) + "\n\n"

        # Everything else
        other_targets = []
        other_targets.extend(self._format_target_list(rects_above, rects))
        other_targets.extend(self._format_target_list(rects_below, rects))

        if len(other_targets) > 0:
            other_targets = "Additional valid interaction targets (not shown) include:\n" + "\n".join(other_targets) + "\n\n"
        else:
            other_targets = ""


        # If there are scrollable elements, then add the corresponding tools
        #has_scrollable_elements = False
        #if has_scrollable_elements:
        #    tools.append(TOOL_SCROLL_ELEMENT_UP)
        #    tools.append(TOOL_SCROLL_ELEMENT_DOWN)

        tool_names = "\n".join([t["function"]["name"] for t in tools])

        text_prompt = f"""
Consider the following screenshot of a web browser, which is open to the page '{self._page.url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

{visible_targets}{other_targets}{focused_hint}You are to respond to the user's most recent request by selecting an appropriate tool the following set, or by answering the question directly if possible:

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
        history.append(self._make_mm_message(text_prompt, scaled_screenshot))
        som_screenshot.close()  # Don't do this if messages start accepting PIL images
        response = self.client.create(messages=history, tools=tools, tool_choice="auto")
        message = response.choices[0].message

        action_description = ""
        self._last_download = None
        try:
            if message.tool_calls:
                # We will only call one tool
                name = message.tool_calls[0].function.name
                args = json.loads(message.tool_calls[0].function.arguments)
                self._log_to_console(fname=name, args=args)

                if name == "visit_url":
                    url = args.get("url")
                    action_description = f"I typed '{url}' into the browser address bar."
                    # Check if the argument starts with a known protocol
                    if url.startswith(("https://", "http://", "file://", "about:")):
                        self._visit_page(url)
                    # If the argument contains a space, treat it as a search query
                    elif " " in url:
                        self._visit_page(f"https://www.bing.com/search?q={quote_plus(url)}&FORM=QBLH")
                    # Otherwise, prefix with https://
                    else:
                        self._visit_page("https://" + url)

                elif name == "history_back":
                    action_description = "I clicked the browser back button."
                    self._back()

                elif name == "web_search":
                    query = args.get("query")
                    action_description = f"I typed '{query}' into the browser search bar."
                    self._visit_page(f"https://www.bing.com/search?q={quote_plus(query)}&FORM=QBLH")

                elif name == "page_up":
                    action_description = "I scrolled up one page in the browser."
                    self._page_up()

                elif name == "page_down":
                    action_description = "I scrolled down one page in the browser."
                    self._page_down()

                elif name == "click":
                    target_id = str(args.get("target_id"))
                    target_name = self._target_name(target_id, rects)
                    if target_name:
                        action_description = f"I clicked '{target_name}'."
                    else:
                        action_description = "I clicked the control."
                    self._click_id(target_id)

                elif name == "input_text":
                    input_field_id = str(args.get("input_field_id"))
                    text_value = str(args.get("text_value"))
                    input_field_name = self._target_name(input_field_id, rects)
                    if input_field_name:
                        action_description = f"I typed '{text_value}' into '{input_field_name}'."
                    else:
                        action_description = f"I input '{text_value}'."
                    self._fill_id(input_field_id, text_value)

                elif name == "scroll_element_up":
                    target_id = str(args.get("target_id"))
                    target_name = self._target_name(target_id, rects)

                    if target_name:
                        action_description = f"I scrolled '{target_name}' up."
                    else:
                        action_description = "I scrolled the control up."

                    self._scroll_id(target_id, "up")

                elif name == "scroll_element_down":
                    target_id = str(args.get("target_id"))
                    target_name = self._target_name(target_id, rects)

                    if target_name:
                        action_description = f"I scrolled '{target_name}' down."
                    else:
                        action_description = "I scrolled the control down."

                    self._scroll_id(target_id, "down")

                elif name == "answer_question":
                    question = str(args.get("question"))
                    action_description = self._summarize_page(question=question)

                elif name == "summarize_page":
                    action_description = self._summarize_page()

                elif name == "sleep":
                    action_description = "I am waiting a short period of time before taking further action."
                    self._sleep(3) # There's a 2s sleep below too

                else:
                    log_event(self, "Unknown tool", error=name)
                    raise ValueError(f"Unknown tool '{name}'. Please choose from:\n\n{tool_names}")

        except ValueError as e:
            if logging_enabled():
                log_event(self, "ValueError", error=str(e))
            return True, str(e)

        self._page.wait_for_load_state()
        self._sleep(3)

        # Handle downloads
        if self._last_download is not None and self.downloads_folder is not None:
            fname = os.path.join(self.downloads_folder, self._last_download.suggested_filename)
            self._last_download.save_as(fname)
            page_body = f"<html><head><title>Download Successful</title></head><body style=\"margin: 20px;\"><h1>Successfully downloaded '{self._last_download.suggested_filename}' to local path:<br><br>{fname}</h1></body></html>"
            self._page.goto("data:text/html;base64," + base64.b64encode(page_body.encode("utf-8")).decode("utf-8"))
            self._page.wait_for_load_state()

        # Handle metadata
        page_metadata = json.dumps(self._get_page_metadata(), indent=4)
        metadata_hash = hashlib.md5(page_metadata.encode("utf-8")).hexdigest()
        if metadata_hash != self._prior_metadata_hash:
            page_metadata = "\nThe following metadata was extracted from the webpage:\n\n" + page_metadata.strip() + "\n"
        else:
            page_metadata = ""
        self._prior_metadata_hash = metadata_hash

        # Describe the viewport of the new page in words
        viewport = self._get_visual_viewport()
        percent_visible = int(viewport["height"] * 100 / viewport["scrollHeight"])
        percent_scrolled = int(viewport["pageTop"] * 100 / viewport["scrollHeight"])
        if percent_scrolled < 1:  # Allow some rounding error
            position_text = "at the top of the page"
        elif percent_scrolled + percent_visible >= 99:  # Allow some rounding error
            position_text = "at the bottom of the page"
        else:
            position_text = str(percent_scrolled) + "% down from the top of the page"

        new_screenshot = self._page.screenshot()
        if self.debug_dir:
            with open(os.path.join(self.debug_dir, "screenshot.png"), "wb") as png:
                png.write(new_screenshot)

        ocr_text = self._get_ocr_text(new_screenshot)
        
        if logging_enabled():
            log_event(self, "cookies", cookies=self._page.context.cookies())
            log_event(
                self,
                "viewport_state",
                page_title=self._page.title(),
                page_url=self._page.url,
                percent_visible=percent_visible,
                percent_scrolled=percent_scrolled,
            )
        # Return the complete observation
        message_content = message.content or ""
        return True, self._make_mm_message(
            f"{message_content}\n\n{action_description}\n\nHere is a screenshot of [{self._page.title()}]({self._page.url}). The viewport shows {percent_visible}% of the webpage, and is positioned {position_text}.{page_metadata}\nAutomatic OCR of the page screenshot has detected the following text:\n\n{ocr_text}".strip(),
            new_screenshot,
        )

    def _image_to_data_uri(self, image):
        """
        Image can be a bytes string, a Binary file-like stream, or PIL Image.
        """
        image_bytes = image
        if isinstance(image, Image.Image):
            image_buffer = io.BytesIO()
            image.save(image_buffer, format="PNG")
            image_bytes = image_buffer.getvalue()
        elif isinstance(image, io.BytesIO):
            image_bytes = image_buffer.getvalue()
        elif isinstance(image, io.BufferedIOBase):
            image_bytes = image.read()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{image_base64}"

    def _make_mm_message(self, text_content, image_content, role="user"):
        return {
            "role": role,
            "content": [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": self._image_to_data_uri(image_content),
                    },
                },
            ],
        }

    def _get_interactive_rects(self):
        try:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
                self._page.evaluate(fh.read())
        except:
            pass
        return self._page.evaluate("MultimodalWebSurfer.getInteractiveRects();")

    def _get_visual_viewport(self):
        try:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
                self._page.evaluate(fh.read())
        except:
            pass
        return self._page.evaluate("MultimodalWebSurfer.getVisualViewport();")

    def _get_focused_rect_id(self):
        try:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
                self._page.evaluate(fh.read())
        except:
            pass
        return self._page.evaluate("MultimodalWebSurfer.getFocusedElementId();")

    def _get_page_metadata(self):
        try:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
                self._page.evaluate(fh.read())
        except:
            pass
        return self._page.evaluate("MultimodalWebSurfer.getPageMetadata();")

    def _get_page_markdown(self):
        html = self._page.evaluate("document.documentElement.outerHTML;")
        res = self._markdown_converter.convert_stream(io.StringIO(html), file_extension=".html", url=self._page.url)
        return res.text_content

    def _on_new_page(self, page):
        self._page = page
        self._page.route(lambda x: True, self._route_handler)
        self._page.on("download", self._download_handler)
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        self._sleep(0.2)
        self._prior_metadata_hash = None
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.wait_for_load_state()
        self._log_to_console(fname="new_tab", args={"url": self._page.url})

    def _back(self):
        self._page.go_back()

    def _visit_page(self, url):
        try:
            # Regular webpage
            self._page.goto(url)
            self._prior_metadata_hash = None
        except Exception as e:
            # Downloaded file
            if self.downloads_folder and "net::ERR_ABORTED" in str(e):
                with self._page.expect_download() as download_info:
                    try:
                        self._page.goto(url)
                    except Exception as e:
                        if "net::ERR_ABORTED" in str(e):
                            pass
                        else:
                            raise e
                    download = download_info.value
                    fname = os.path.join(self.downloads_folder, download.suggested_filename)
                    download.save_as(fname)
                    message = f"<body style=\"margin: 20px;\"><h1>Successfully downloaded '{download.suggested_filename}' to local path:<br><br>{fname}</h1></body>"
                    self._page.goto("data:text/html;base64," + base64.b64encode(message.encode("utf-8")).decode("utf-8"))
                    self._last_download = None # Since we already handled it
            else:
                raise e

    def _page_down(self):
        self._page.evaluate(f"window.scrollBy(0, {VIEWPORT_HEIGHT-50});")

    def _page_up(self):
        self._page.evaluate(f"window.scrollBy(0, -{VIEWPORT_HEIGHT-50});")

    def _click_id(self, identifier):
        target = self._page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            target.wait_for(timeout=100)
        except TimeoutError:
            raise ValueError("No such element.")

        # Click it
        target.scroll_into_view_if_needed()
        box = target.bounding_box()
        try:
            # Give it a chance to open a new page
            with self._page.expect_event("popup", timeout=1000) as page_info:
                self._page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, delay=10)
                self._on_new_page(page_info.value)
        except TimeoutError:
            pass

    def _fill_id(self, identifier, value):
        target = self._page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            target.wait_for(timeout=100)
        except TimeoutError:
            raise ValueError("No such element.")

        # Fill it
        target.scroll_into_view_if_needed()
        target.focus()
        try:
            target.fill(value)
        except PlaywrightError:
            target.press_sequentially(value)
        target.press("Enter")


    def _scroll_id(self, identifier, direction):
        self._page.evaluate(
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

    def _summarize_page(self, question=None, token_limit=100000):
        page_markdown = self._get_page_markdown()

        buffer = ""
        for line in re.split(r"([\r\n]+)", page_markdown):
            tokens = count_token(buffer + line)
            if tokens + 1024 > token_limit:  # Leave room for our summary
                break
            buffer += line

        buffer = buffer.strip()
        if len(buffer) == 0:
            return "Nothing to summarize."

        title = self._page.url
        try:
            title = self._page.title()
        except:
            pass

        # Take a screenshot and scale it
        screenshot = self._page.screenshot()
        if not isinstance(screenshot, io.BufferedIOBase):
            screenshot = io.BytesIO(screenshot)
        screenshot = Image.open(screenshot)
        scaled_screenshot = screenshot.resize((MLM_WIDTH, MLM_HEIGHT))
        screenshot.close()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that can summarize long documents to answer question.",
            }
        ]

        prompt = f"We are visiting the webpage '{title}'. Its full-text contents are pasted below, along with a screenshot of the page's current viewport."
        if question is not None:
            prompt += (
                f" Please summarize the webpage into one or two paragraphs with respect to '{question}':\n\n{buffer}"
            )
        else:
            prompt += f" Please summarize the webpage into one or two paragraphs:\n\n{buffer}"

        messages.append(
            self._make_mm_message(prompt, scaled_screenshot),
        )
        scaled_screenshot.close()

        response = self.client.create(context=None, messages=messages)
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        return str(extracted_response)


    def _get_ocr_text(self, image):
        
        scaled_screenshot = None
        if isinstance(image, Image.Image):
            scaled_screenshot = image.resize((MLM_WIDTH, MLM_HEIGHT))
        else:
            pil_image = None
            if not isinstance(image, io.BufferedIOBase):
                pil_image = Image.open(io.BytesIO(image))
            else:
                pil_image = Image.open(image)
            scaled_screenshot = pil_image.resize((MLM_WIDTH, MLM_HEIGHT))
            pil_image.close()

        messages = [
            self._make_mm_message("""
            Please transcribe all visible text on this viewport, including both main content and the labels of UI elements.
            Do not hallucinate text that is not present. E.g., if a sentence/text is cutoff at the edge of the viewport,
            do not try to complete it. Only transcribe text that is absolutely clearly and completely visible. But for the text
            that is incomplete say something like
            
                                  <rest of the text is cut off from direction {X} on the page>.
                                  
            But please do not hallucinate that text-- the transcription will be used for medical tasks and the consequences can be fatal.
            When there is text that is incomplete/cut off, you must indicate that in the transcription. Skipping this will make 
            physicians think that all content was captured/transcribed, leading to incorrect decisions.      
            """
            , scaled_screenshot),
        ]
        scaled_screenshot.close()

        response = self.client.create(context=None, messages=messages)
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        return str(extracted_response)


    #def _get_ocr_text(self, image, ocr_min_confidence=0.5):
    #    pil_image = None
    #
    #    if isinstance(image, Image.Image):
    #        pil_image = image
    #    else:
    #        if not isinstance(image, io.BufferedIOBase):
    #            pil_image = Image.open(io.BytesIO(image))
    #        else:
    #            pil_image = Image.open(image)
    #    
    #    # Remove transparency
    #    if pil_image.mode in ("RGBA", "P"):
    #        tmp = pil_image.convert("RGB")
    #        pil_image.close()
    #        pil_image = tmp
    #
    #    output = self._ocr_reader.readtext(np.array(pil_image))
    #        # The output is a list of tuples, each containing the coordinates of the text and the text itself.
    #        # We join all the text pieces together to get the final text.
    #    ocr_text = " "
    #    for item in output:
    #        if item[2] >= ocr_min_confidence:
    #            ocr_text += item[1] + "\n"
    #    ocr_text = ocr_text.strip()
    #
    #    if not isinstance(image, Image.Image):
    #        # If we created the image, then close it
    #        pil_image.close()
    #
    #    print(ocr_text)
    #    return ocr_text


    def _log_to_console(self, fname, args):
        if fname is None or fname == "":
            fname = "[unknown]"
        if args is None:
            args = {}

        _arg_strs = []
        for a in args:
            _arg_strs.append(a + "='" + str(args[a]) + "'")

        if logging_enabled():
            log_event(self, "browser_action", action=fname, args=args)

        print(
            colored("\n>>>>>>>> BROWSER ACTION " + fname + "(" + ", ".join(_arg_strs) + ")", "cyan"),
            flush=True,
        )
