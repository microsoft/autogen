# ruff: noqa: E722
import re
import time
import os
import json
import io
import base64
import pathlib
from PIL import Image
from urllib.parse import urlparse, quote, quote_plus, unquote, urlunparse, parse_qs
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple
from typing_extensions import Annotated
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from .... import Agent, ConversableAgent, OpenAIWrapper
from ....runtime_logging import logging_enabled, log_event
from ....code_utils import content_str
from .state_of_mark import add_state_of_mark

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

# State-of-mark IDs for static browser controls
MARK_ID_ADDRESS_BAR = 0
MARK_ID_BACK = 1
MARK_ID_RELOAD = 2
MARK_ID_SEARCH_BAR = 3
MARK_ID_PAGE_UP = 4
MARK_ID_PAGE_DOWN = 5


class MultimodalWebSurferAgent(ConversableAgent):
    """(In preview) A multimodal agent that acts as a web surfer that can search the web and visit web pages."""

    DEFAULT_DESCRIPTION = "A helpful assistant with access to a web browser. Ask them to perform web searches, open pages, and interact with content (e.g., clicking links, scrolling the viewport, etc., filling in form fields, etc.)"

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
        mlm_config: Optional[Union[Dict, Literal[False]]] = None,  # TODO: Remove this
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        headless: bool = True,
        browser_channel=DEFAULT_CHANNEL,
        browser_data_dir: Optional[str] = None,
        start_page: Optional[str] = None,
        debug_dir: Optional[str] = None,
        navigation_allow_list = lambda url: True,
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

        # self._mlm_config = mlm_config
        # self._mlm_client = OpenAIWrapper(**self._mlm_config)
        self.start_page = start_page or self.DEFAULT_START_PAGE
        self.debug_dir = debug_dir or os.getcwd()

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
                        body="<html><body><h1>Navigation Blocked</h1><p>Navigation was blocked by the client. Click the <a href=\"javascript: history.back()\">browser back button</a> to go back, return Home to <a href=\"" + self.start_page + "\">" + self.start_page + "</a>.</p></body></html>")
                else:
                    route.fulfill(response=response)
        self._route_handler = _route_handler

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
        self._page = self._context.new_page()
        self._page.route(lambda x: True, self._route_handler)
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.goto(self.start_page)
        self._page.wait_for_load_state()
        time.sleep(1)

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
        self._visit_page(self.start_page)

    def generate_surfer_reply(
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
        som_screenshot, visible_rects = add_state_of_mark(self._page.screenshot(), rects)

        if self.debug_dir:
            som_screenshot.save(os.path.join(self.debug_dir, "screenshot.png"))

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
                + "currently has the input focus.\n"
            )

        # Include all the static elements
        text_labels = f"""
  {{ "id": {MARK_ID_BACK}, "aria-role": "button", "html_tag": "button", "actions": ["click"], "name": "browser back button" }},
  {{ "id": {MARK_ID_ADDRESS_BAR}, "aria-role": "textbox",   "html_tag": "input, type=text", "actions": ["type"],  "name": "browser address input" }},
  {{ "id": {MARK_ID_SEARCH_BAR}, "aria-role": "searchbox", "html_tag": "input, type=text", "actions": ["type"],  "name": "browser web search input" }},"""

        # We can scroll up
        if viewport["pageTop"] > 5:
            text_labels += f"""
  {{ "id": {MARK_ID_PAGE_UP}, "aria-role": "scrollbar", "html_tag": "button", "actions": ["click", "scroll_up"], "name": "browser scroll up control" }},"""

        # Can scroll down
        if (viewport["pageTop"] + viewport["height"] + 5) < viewport["scrollHeight"]:
            text_labels += f"""
  {{ "id": {MARK_ID_PAGE_DOWN}, "aria-role": "scrollbar", "html_tag": "button", "actions": ["click", "scroll_down"], "name": "browser scroll down control" }},"""

        # Everything visible
        for r in visible_rects:
            if r in rects:
                actions = ["'click'"]
                if rects[r]["role"] in ["textbox", "searchbox", "search"]:
                    actions = ["'type'"]
                if rects[r]["v-scrollable"]:
                    actions.append("'scroll_up'")
                    actions.append("'scroll_down'")
                actions = "[" + ",".join(actions) + "]"

                text_labels += f"""
   {{ "id": {r}, "aria-role": "{rects[r]['role']}", "html_tag": "{rects[r]['tag_name']}", "actions": "{actions}", "name": "{rects[r]['aria-name']}" }},"""

        text_prompt = f"""
Consider the following screenshot of a web browser, which is open to the page '{self._page.url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

[
{text_labels}
]
{focused_hint}
You are to respond to the user's most recent request by selecting a browser action to perform. Please output the appropriate action in the following format:

TARGET:   <id of interactive element>
ACTION:   <One single action from the element's list of actions>
ARGUMENT: <The action' argument, if any. For example, the text to type if the action is typing>
""".strip()

        # Scale the screenshot for the MLM, and close the original
        scaled_screenshot = som_screenshot.resize((MLM_WIDTH, MLM_HEIGHT))
        som_screenshot.close()
        if self.debug_dir:
            scaled_screenshot.save(os.path.join(self.debug_dir, "screenshot_scaled.png"))

        # Add the multimodal message and make the request
        history.append(self._make_mm_message(text_prompt, scaled_screenshot))
        som_screenshot.close()  # Don't do this if messages start accepting PIL images
        response = self.client.create(messages=history)
        text_response = "\n" + self.client.extract_text_or_completion_object(response)[0].strip() + "\n"

        target = None
        target_name = None
        m = re.search(r"\nTARGET:\s*(.*?)\n", text_response)
        if m:
            target = m.group(1).strip()

            # Non-critical. Mainly for pretty logs
            target_name = rects.get(target, {}).get("aria-name")
            if target_name:
                target_name = target_name.strip()

        action = None
        m = re.search(r"\nACTION:\s*(.*?)\n", text_response)
        if m:
            action = m.group(1).strip().lower()

        m = re.search(r"\nARGUMENT:\s*(.*?)\n", text_response)
        if m:
            argument = m.group(1).strip()

        action_description = ""
        try:
            if target == str(MARK_ID_ADDRESS_BAR) and argument:
                action_description = f"I typed '{argument}' into the browser address bar."
                self._log_to_console("goto", arg=argument)
                # Check if the argument starts with a known protocol
                if argument.startswith(("https://", "http://", "file://", "about:")):
                    self._visit_page(argument)
                # If the argument contains a space, treat it as a search query
                elif " " in argument:
                    self._visit_page(f"https://www.bing.com/search?q={quote_plus(argument)}&FORM=QBLH")
                # Otherwise, prefix with https://
                else:
                    argument = "https://" + argument
                    self._visit_page(argument)
            elif target == str(MARK_ID_BACK):
                action_description = "I clicked the browser back button."
                self._log_to_console("back")
                self._back()
            elif target == str(MARK_ID_SEARCH_BAR) and argument:
                action_description = f"I typed '{argument}' into the browser search bar."
                self._log_to_console("search", arg=argument)
                self._visit_page(f"https://www.bing.com/search?q={quote_plus(argument)}&FORM=QBLH")
            elif target == str(MARK_ID_PAGE_UP):
                action_description = "I scrolled up one screen in the browser."
                self._log_to_console("page_up")
                self._page_up()
            elif target == str(MARK_ID_PAGE_DOWN):
                action_description = "I scrolled down one screen in the browser."
                self._log_to_console("page_down")
                self._page_down()
            elif action == "click":
                if target_name:
                    action_description = f"I clicked '{target_name}'."
                else:
                    action_description = "I clicked the control."
                self._log_to_console("click", target=target_name if target_name else target)
                self._click_id(target)
            elif action == "type":
                if target_name:
                    action_description = f"I typed '{argument}' into '{target_name}'."
                else:
                    action_description = f"I input '{argument}'."
                self._log_to_console("type", target=target_name if target_name else target, arg=argument)
                self._fill_id(target, argument if argument else "")
            elif action == "scroll_up":
                if target_name:
                    action_description = f"I scrolled '{target_name}' up."
                else:
                    action_description = "I scrolled the control up."
                self._log_to_console("scroll_up", target=target_name if target_name else target)
                self._scroll_id(target, "up")
            elif action == "scroll_down":
                if target_name:
                    action_description = f"I scrolled '{target_name}' down."
                else:
                    action_description = "I scrolled the control down."
                self._log_to_console("scroll_down", target=target_name if target_name else target)
                self._scroll_id(target, "down")
            else:
                self._log_to_console("no_action", target=target_name if target_name else target)
                # No action
                return True, text_response
        except ValueError as e:
            if logging_enabled():
                log_event(self, "ValueError", error=str(e))
            return True, str(e)

        self._page.wait_for_load_state()
        time.sleep(1)

        # Descrive the viewport of the new page in words
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
        return True, self._make_mm_message(
            f"{action_description} Here is a screenshot of [{self._page.title()}]({self._page.url}). The viewport shows {percent_visible}% of the webpage, and is positioned {position_text}.".strip(),
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

    def _make_mm_message(self, text_content, image_content):
        return {
            "role": "user",
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

    def _on_new_page(self, page):
        self._page = page
        self._page.route(lambda x: True, self._route_handler)
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        time.sleep(0.2)
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.wait_for_load_state()

        title = None
        try:
            title = self._page.title()
        except:
            pass

        self._log_to_console("new_tab", arg=title if title else self._page.url)

    def _back(self):
        self._page.go_back()

    def _visit_page(self, url):
        self._page.goto(url)

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
        box = target.bounding_box()
        try:
            # Give it a chance to open a new page
            with self._page.expect_event("popup", timeout=1000) as page_info:
                self._page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
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
        target.focus()
        target.fill(value)
        self._page.keyboard.press("Enter")

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


    def _log_to_console(self, action, target="", arg=""):

        if target is None:
            target = ""
        if arg is None:
            arg = ""

        if logging_enabled():
            log_event(self, "browser_action", action=action, target=target, arg=arg)

        if len(target) > 50:
            target = target[0:47] + "..."
        if len(arg) > 50:
            arg = arg[0:47] + "..."
        log_str = action + "("
        if target:
            log_str += '"' + re.sub(r"\s+", " ", target).strip() + '",'
        if arg:
            log_str += '"' + re.sub(r"\s+", " ", arg).strip() + '"'
        log_str = log_str.rstrip(",") + ")"
        print(
            colored("\n>>>>>>>> BROWSER ACTION " + log_str, "cyan"),
            flush=True,
        )
