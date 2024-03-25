# ruff: noqa: E722
import copy
import re
import time
import logging
import os
import json
import io
import random
import base64
import pathlib
from urllib.parse import urlparse, quote, quote_plus, unquote, urlunparse, parse_qs
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple
from typing_extensions import Annotated
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from PIL import Image, ImageDraw, ImageFont
from .... import Agent, ConversableAgent, AssistantAgent, UserProxyAgent, GroupChatManager, GroupChat, OpenAIWrapper
from ....browser_utils import AbstractMarkdownBrowser, RequestsMarkdownBrowser, BingMarkdownSearch
from ....code_utils import content_str
from ....token_count_utils import count_token, get_max_token_limit
from ....oai.openai_utils import filter_config

logger = logging.getLogger(__name__)

# Sentinels for constructor
DEFAULT_CHANNEL = object()

# Viewport dimensions
VIEWPORT_HEIGHT = 1080
VIEWPORT_WIDTH = 1920

# Size of the image we send to the MLM
# Current values represent a 2/3 scaling to fit within the GPT-4v short-edge constraints (768px)
MLM_HEIGHT = 720
MLM_WIDTH = 1280

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
        mlm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        headless=True,
        chromium_channel=DEFAULT_CHANNEL,
        chromium_data_dir=None,
        start_page="https://www.bing.com/",
        debug_dir=os.getcwd(),
    ):
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
        self.start_page = start_page
        self.debug_dir = debug_dir

        # Create the playwright instance
        launch_args = {"headless": headless}
        if chromium_channel is not DEFAULT_CHANNEL:
            launch_args["channel"] = chromium_channel
        self._playwright = sync_playwright().start()

        # Create the context -- are we launching a persistent instance?
        if chromium_data_dir is None:
            browser = self._playwright.chromium.launch(**launch_args)
            self._context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
            )
        else:
            self._context = self._playwright.chromium.launch_persistent_context(chromium_data_dir, **launch_args)

        # Create the page
        self._page = self._context.new_page()
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.goto(self.start_page)
        self._page.wait_for_load_state()
        time.sleep(1)

        # Prepare the debug directory -- which stores the screenshots generated throughout the process
        if self.debug_dir:
            if not os.path.isdir(self.debug_dir):
                os.mkdir(self.debug_dir)
            debug_html = os.path.join(self.debug_dir, "screenshot.html")
            with open(debug_html, "wt") as fh:
                fh.write(
                    """
<html style="width:100%; margin: 0px; padding: 0px;">
<body style="width: 100%; margin: 0px; padding: 0px;">
    <img src="screenshot.png" id="main_image" style="width: 100%; margin: 0px; padding: 0px;">
    <script language="JavaScript">
var counter = 0;
setInterval(function() {
   counter += 1;
   document.getElementById("main_image").src = "screenshot.png?bc=" + counter;
}, 300);
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

    def generate_surfer_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        # Clone the messages to give context
        history = [m for m in messages]

        # Ask the page for interactive elements, then prepare the state-of-mark screenshot
        rects = self._get_interactive_rects()
        screenshot, visible_rects = self._som_screenshot(rects, url=self._page.url)

        if self.debug_dir:
            screenshot.save(os.path.join(self.debug_dir, "screenshot.png"))

        # Include all the static elements
        text_labels = f"""
  {{ "id": {MARK_ID_BACK}, "aria-role": "button", "html_tag": "button", "actions": ["click"], "name": "browser back button" }},
  {{ "id": {MARK_ID_ADDRESS_BAR}, "aria-role": "textbox",   "html_tag": "input, type=text", "actions": ["type"],  "name": "browser address input" }},
  {{ "id": {MARK_ID_SEARCH_BAR}, "aria-role": "searchbox", "html_tag": "input, type=text", "actions": ["type"],  "name": "browser web search input" }},
  {{ "id": {MARK_ID_PAGE_UP}, "aria-role": "scrollbar", "html_tag": "button", "actions": ["click"], "name": "browser scroll up control" }},
  {{ "id": {MARK_ID_PAGE_DOWN}, "aria-role": "scrollbar", "html_tag": "button", "actions": ["click"], "name": "browser scroll down control" }},"""

        for r in visible_rects:
            if r in rects:
                actions = '["click"]'
                if rects[r]["role"] in ["textbox", "searchbox", "search"]:
                    actions = '["type"]'
                text_labels += f"""
   {{ "id": {r}, "aria-role": "{rects[r]['role']}", "html_tag": "{rects[r]['tag_name']}", "actions": "{actions}", "name": "{rects[r]['aria-name']}" }},"""

        text_prompt = f"""
Consider the following screenshot of a web browser, which is open to the page '{self._page.url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

[
{text_labels}
]

You are to respond to the user's most recent request by selecting a browser action to perform. Please output the appropriate action in the following format:

TARGET:   <id of interactive element>
ACTION:   <One single action from the element's list of actions>
ARGUMENT: <The action' argument, if any. For example, the text to type if the action is typing>
""".strip()

        scaled_screenshot = screenshot.resize((MLM_WIDTH, MLM_HEIGHT))
        if self.debug_dir:
            scaled_screenshot.save(os.path.join(self.debug_dir, "screenshot_scaled.png"))

        history.append(self._make_mm_message(text_prompt, scaled_screenshot))
        response = self.client.create(messages=history)
        text_response = "\n" + self.client.extract_text_or_completion_object(response)[0].strip() + "\n"

        target = None
        m = re.search(r"\nTARGET:\s*(.*?)\n", text_response)
        if m:
            target = m.group(1).strip()

        action = None
        m = re.search(r"\nACTION:\s*(.*?)\n", text_response)
        if m:
            action = m.group(1).strip().lower()

        m = re.search(r"\nARGUMENT:\s*(.*?)\n", text_response)
        if m:
            argument = m.group(1).strip()

        if target == str(MARK_ID_ADDRESS_BAR) and argument:
            if argument.startswith("https://") or argument.startswith("http://"):
                self._visit_page(argument)
            else:
                self._visit_page(f"https://www.bing.com/search?q={quote_plus(argument)}&FORM=QBLH")
        elif target == str(MARK_ID_SEARCH_BAR) and argument:
            self._visit_page(f"https://www.bing.com/search?q={quote_plus(argument)}&FORM=QBLH")
        elif target == str(MARK_ID_PAGE_UP):
            self._page_up()
        elif target == str(MARK_ID_PAGE_DOWN):
            self._page_down()
        elif action == "click":
            self._click_id(target)
        elif action == "type":
            self._fill_id(target, argument if argument else "")
        else:
            # No action
            return True, text_response

        self._page.wait_for_load_state()
        time.sleep(1)

        if self.debug_dir:
            new_screenshot = self._page.screenshot()
            with open(os.path.join(self.debug_dir, "screenshot.png"), "wb") as png:
                png.write(new_screenshot)

        return True, self._make_mm_message(
            f"Here is a screenshot of '{self._page.title()}' ({self._page.url}).", new_screenshot
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

    def _som_screenshot(self, rectangles, url=None):
        if url is None:
            url = self._page.url

        visible_rects = list()

        fnt = ImageFont.load_default(14)
        screenshot_bytes = io.BytesIO(self._page.screenshot())
        base = Image.open(screenshot_bytes).convert("L").convert("RGBA")
        overlay = Image.new("RGBA", base.size)

        draw = ImageDraw.Draw(overlay)
        for r in rectangles:
            for rect in rectangles[r]["rects"]:
                # Empty rectangles
                if not rect:
                    continue
                if rect["width"] * rect["height"] == 0:
                    continue

                mid = ((rect["right"] + rect["left"]) / 2.0, (rect["top"] + rect["bottom"]) / 2.0)

                if 0 <= mid[0] and mid[0] < VIEWPORT_WIDTH and 0 <= mid[1] and mid[1] < VIEWPORT_HEIGHT:
                    visible_rects.append(r)

                self._draw_roi(draw, int(r), fnt, rect)

        comp = Image.alpha_composite(base, overlay)
        return comp, visible_rects

    def _trim_drawn_text(self, draw, text, font, max_width):
        buff = ""
        for c in text:
            tmp = buff + c
            bbox = draw.textbbox((0, 0), tmp, font=font, anchor="lt", align="left")
            width = bbox[2] - bbox[0]
            if width > max_width:
                return buff
            buff = tmp
        return buff

    def _draw_roi(self, draw, idx, font, rect):
        color = self._color(idx)
        luminance = color[0] * 0.3 + color[1] * 0.59 + color[2] * 0.11
        text_color = (0, 0, 0, 255) if luminance > 90 else (255, 255, 255, 255)

        roi = [(rect["left"], rect["top"]), (rect["right"], rect["bottom"])]
        anchor = (rect["right"], rect["top"])

        draw.rectangle(roi, outline=color, fill=(color[0], color[1], color[2], 48), width=2)

        bbox = draw.textbbox(anchor, str(idx), font=font, anchor="rb", align="center")
        bbox = (bbox[0] - 3, bbox[1] - 3, bbox[2] + 3, bbox[3] + 3)
        draw.rectangle(bbox, fill=color)

        draw.text(anchor, str(idx), fill=text_color, font=font, anchor="rb", align="center")

    def _color(self, identifier):
        rnd = random.Random(int(identifier))
        color = [rnd.randint(0, 255), rnd.randint(125, 255), rnd.randint(0, 50)]
        rnd.shuffle(color)
        color.append(255)
        return tuple(color)

    def _on_new_page(self, page):
        self._page = page
        self._page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        self._page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        self._page.wait_for_load_state()

    def _get_interactive_rects(self):
        try:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
                self._page.evaluate(fh.read())
        except:
            pass
        return self._page.evaluate("MultimodalWebSurfer.getInteractiveRects();")

    def _visit_page(self, url):
        self._page.goto(url)

    def _page_down(self):
        self._page.evaluate(f"window.scrollBy(0, {VIEWPORT_HEIGHT-50});")

    def _page_up(self):
        self._page.evaluate(f"window.scrollBy(0, -{VIEWPORT_HEIGHT-50});")

    def _click_id(self, identifier):
        target = self._page.locator(f"[__elementId='{identifier}']")
        if target:
            box = target.bounding_box()
            try:
                with self._page.expect_event("popup", timeout=1000) as page_info:
                    self._page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                self._on_new_page(page_info.value)
            except TimeoutError:
                pass
        else:
            return "No such element."

    def _fill_id(self, identifier, value):
        target = self._page.locator(f"[__elementId='{identifier}']")
        if target:
            target.focus()
            target.fill(value)
            self._page.keyboard.press("Enter")
