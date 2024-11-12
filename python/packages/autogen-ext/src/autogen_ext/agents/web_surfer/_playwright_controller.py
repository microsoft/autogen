import base64
import hashlib
import io
import json
import logging
import os
import asyncio
import re
import time
import traceback
from typing import (
    Any,
    BinaryIO,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

# Any, Callable, Dict, List, Literal, Tuple
from urllib.parse import quote_plus  # parse_qs, quote, unquote, urlparse, urlunparse

import aiofiles
import PIL.Image
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage, MultiModalMessage, ResetMessage, TextMessage
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components import Image as AGImage
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from playwright._impl._errors import Error as PlaywrightError
from playwright._impl._errors import TimeoutError
from playwright.async_api import BrowserContext, Download, Page, Playwright, async_playwright

from ._events import WebSurferEvent
from ._set_of_mark import add_set_of_mark
from ._tool_definitions import (
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
from ._types import (
    InteractiveRegion,
    UserContent,
    VisualViewport,
    interactiveregion_from_dict,
    visualviewport_from_dict,
)
from ._utils import message_content_to_str

# Viewport dimensions
VIEWPORT_HEIGHT = 900
VIEWPORT_WIDTH = 1440

# Size of the image we send to the MLM
# Current values represent a 0.85 scaling to fit within the GPT-4v short-edge constraints (768px)
MLM_HEIGHT = 765
MLM_WIDTH = 1224

SCREENSHOT_TOKENS = 1105


class PlaywrightController:
    def __init__(
        self,
        downloads_folder: Optional[str] = None,
    ) -> None:
        s
        
        

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
                        source=self.name,
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

