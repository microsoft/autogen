import asyncio
import base64
import os
import random
from typing import Any, Callable, Dict, Optional, Tuple, Union, cast

from playwright._impl._errors import Error as PlaywrightError
from playwright._impl._errors import TimeoutError
from playwright.async_api import Download, Page

from ._types import (
    InteractiveRegion,
    VisualViewport,
    interactiveregion_from_dict,
    visualviewport_from_dict,
)


class PlaywrightController:
    def __init__(
        self,
        animate_actions: bool = False,
        downloads_folder: Optional[str] = None,
        viewport_width: int = 1440,
        viewport_height: int = 900,
        _download_handler: Optional[Callable[[Download], None]] = None,
        to_resize_viewport: bool = True,
    ) -> None:
        """
        A controller for Playwright to interact with web pages.
        animate_actions: If True, actions will be animated.
        downloads_folder: The folder to save downloads to.
        viewport_width: The width of the viewport.
        viewport_height: The height of the viewport.
        _download_handler: A handler for downloads.
        to_resize_viewport: If True, the viewport will be resized.
        """
        self.animate_actions = animate_actions
        self.downloads_folder = downloads_folder
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._download_handler = _download_handler
        self.to_resize_viewport = to_resize_viewport
        self._page_script: str = ""
        self.last_cursor_position: Tuple[float, float] = (0.0, 0.0)

        # Read page_script
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"), "rt") as fh:
            self._page_script = fh.read()

    async def sleep(self, page: Page, duration: Union[int, float]) -> None:
        assert page is not None
        await page.wait_for_timeout(duration * 1000)

    async def get_interactive_rects(self, page: Page) -> Dict[str, InteractiveRegion]:
        assert page is not None
        # Read the regions from the DOM
        try:
            await page.evaluate(self._page_script)
        except Exception:
            pass
        result = cast(Dict[str, Dict[str, Any]], await page.evaluate("MultimodalWebSurfer.getInteractiveRects();"))

        # Convert the results into appropriate types
        assert isinstance(result, dict)
        typed_results: Dict[str, InteractiveRegion] = {}
        for k in result:
            assert isinstance(k, str)
            typed_results[k] = interactiveregion_from_dict(result[k])

        return typed_results

    async def get_visual_viewport(self, page: Page) -> VisualViewport:
        assert page is not None
        try:
            await page.evaluate(self._page_script)
        except Exception:
            pass
        return visualviewport_from_dict(await page.evaluate("MultimodalWebSurfer.getVisualViewport();"))

    async def get_focused_rect_id(self, page: Page) -> str:
        assert page is not None
        try:
            await page.evaluate(self._page_script)
        except Exception:
            pass
        result = await page.evaluate("MultimodalWebSurfer.getFocusedElementId();")
        return str(result)

    async def get_page_metadata(self, page: Page) -> Dict[str, Any]:
        assert page is not None
        try:
            await page.evaluate(self._page_script)
        except Exception:
            pass
        result = await page.evaluate("MultimodalWebSurfer.getPageMetadata();")
        assert isinstance(result, dict)
        return cast(Dict[str, Any], result)

    async def on_new_page(self, page: Page) -> None:
        assert page is not None
        page.on("download", self._download_handler)  # type: ignore
        if self.to_resize_viewport and self.viewport_width and self.viewport_height:
            await page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})
        await self.sleep(page, 0.2)
        await page.add_init_script(path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "page_script.js"))
        await page.wait_for_load_state()

    async def back(self, page: Page) -> None:
        assert page is not None
        await page.go_back()

    async def visit_page(self, page: Page, url: str) -> Tuple[bool, bool]:
        assert page is not None
        reset_prior_metadata_hash = False
        reset_last_download = False
        try:
            # Regular webpage
            await page.goto(url)
            await page.wait_for_load_state()
            reset_prior_metadata_hash = True
        except Exception as e_outer:
            # Downloaded file
            if self.downloads_folder and "net::ERR_ABORTED" in str(e_outer):
                async with page.expect_download() as download_info:
                    try:
                        await page.goto(url)
                    except Exception as e_inner:
                        if "net::ERR_ABORTED" in str(e_inner):
                            pass
                        else:
                            raise e_inner
                    download = await download_info.value
                    fname = os.path.join(self.downloads_folder, download.suggested_filename)
                    await download.save_as(fname)
                    message = f"<body style=\"margin: 20px;\"><h1>Successfully downloaded '{download.suggested_filename}' to local path:<br><br>{fname}</h1></body>"
                    await page.goto(
                        "data:text/html;base64," + base64.b64encode(message.encode("utf-8")).decode("utf-8")
                    )
                    reset_last_download = True
            else:
                raise e_outer
        return reset_prior_metadata_hash, reset_last_download

    async def page_down(self, page: Page) -> None:
        assert page is not None
        await page.evaluate(f"window.scrollBy(0, {self.viewport_height-50});")

    async def page_up(self, page: Page) -> None:
        assert page is not None
        await page.evaluate(f"window.scrollBy(0, -{self.viewport_height-50});")

    async def gradual_cursor_animation(
        self, page: Page, start_x: float, start_y: float, end_x: float, end_y: float
    ) -> None:
        # animation helper
        steps = 20
        for step in range(steps):
            x = start_x + (end_x - start_x) * (step / steps)
            y = start_y + (end_y - start_y) * (step / steps)
            # await page.mouse.move(x, y, steps=1)
            await page.evaluate(f"""
                (function() {{
                    let cursor = document.getElementById('red-cursor');
                    cursor.style.left = '{x}px';
                    cursor.style.top = '{y}px';
                }})();
            """)
            await asyncio.sleep(0.05)

        self.last_cursor_position = (end_x, end_y)

    async def add_cursor_box(self, page: Page, identifier: str) -> None:
        # animation helper
        await page.evaluate(f"""
            (function() {{
                let elm = document.querySelector("[__elementId='{identifier}']");
                if (elm) {{
                    elm.style.transition = 'border 0.3s ease-in-out';
                    elm.style.border = '2px solid red';
                }}
            }})();
        """)
        await asyncio.sleep(0.3)

        # Create a red cursor
        await page.evaluate("""
            (function() {
                let cursor = document.createElement('div');
                cursor.id = 'red-cursor';
                cursor.style.width = '10px';
                cursor.style.height = '10px';
                cursor.style.backgroundColor = 'red';
                cursor.style.position = 'absolute';
                cursor.style.borderRadius = '50%';
                cursor.style.zIndex = '10000';
                document.body.appendChild(cursor);
            })();
        """)

    async def remove_cursor_box(self, page: Page, identifier: str) -> None:
        # Remove the highlight and cursor
        await page.evaluate(f"""
            (function() {{
                let elm = document.querySelector("[__elementId='{identifier}']");
                if (elm) {{
                    elm.style.border = '';
                }}
                let cursor = document.getElementById('red-cursor');
                if (cursor) {{
                    cursor.remove();
                }}
            }})();
        """)

    async def click_id(self, page: Page, identifier: str) -> Page | None:
        """
        Returns new page if a new page is opened, otherwise None.
        """
        new_page: Page | None = None
        assert page is not None
        target = page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=5000)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Click it
        await target.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)

        box = cast(Dict[str, Union[int, float]], await target.bounding_box())

        if self.animate_actions:
            await self.add_cursor_box(page, identifier)
            # Move cursor to the box slowly
            start_x, start_y = self.last_cursor_position
            end_x, end_y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            await self.gradual_cursor_animation(page, start_x, start_y, end_x, end_y)
            await asyncio.sleep(0.1)

            try:
                # Give it a chance to open a new page
                async with page.expect_event("popup", timeout=1000) as page_info:  # type: ignore
                    await page.mouse.click(end_x, end_y, delay=10)
                    new_page = await page_info.value  # type: ignore
                    assert isinstance(new_page, Page)
                    await self.on_new_page(new_page)
            except TimeoutError:
                pass
            await self.remove_cursor_box(page, identifier)

        else:
            try:
                # Give it a chance to open a new page
                async with page.expect_event("popup", timeout=1000) as page_info:  # type: ignore
                    await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, delay=10)
                    new_page = await page_info.value  # type: ignore
                    assert isinstance(new_page, Page)
                    await self.on_new_page(new_page)
            except TimeoutError:
                pass
        return new_page  # type: ignore

    async def hover_id(self, page: Page, identifier: str) -> None:
        """
        Hovers the mouse over the target with the given id.
        """
        assert page is not None
        target = page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=5000)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Hover over it
        await target.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)

        box = cast(Dict[str, Union[int, float]], await target.bounding_box())

        if self.animate_actions:
            await self.add_cursor_box(page, identifier)
            # Move cursor to the box slowly
            start_x, start_y = self.last_cursor_position
            end_x, end_y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            await self.gradual_cursor_animation(page, start_x, start_y, end_x, end_y)
            await asyncio.sleep(0.1)
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            await self.remove_cursor_box(page, identifier)
        else:
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    async def fill_id(self, page: Page, identifier: str, value: str) -> None:
        assert page is not None
        target = page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=5000)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Fill it
        await target.scroll_into_view_if_needed()
        box = cast(Dict[str, Union[int, float]], await target.bounding_box())

        if self.animate_actions:
            await self.add_cursor_box(page, identifier)
            # Move cursor to the box slowly
            start_x, start_y = self.last_cursor_position
            end_x, end_y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            await self.gradual_cursor_animation(page, start_x, start_y, end_x, end_y)
            await asyncio.sleep(0.1)

        # Focus on the element
        await target.focus()
        if self.animate_actions:
            # fill char by char to mimic human speed for short text and type fast for long text
            if len(value) < 100:
                delay_typing_speed = 50 + 100 * random.random()
            else:
                delay_typing_speed = 10
            await target.press_sequentially(value, delay=delay_typing_speed)
        else:
            try:
                await target.fill(value)
            except PlaywrightError:
                await target.press_sequentially(value)
        await target.press("Enter")

        if self.animate_actions:
            await self.remove_cursor_box(page, identifier)

    async def scroll_id(self, page: Page, identifier: str, direction: str) -> None:
        assert page is not None
        await page.evaluate(
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

    async def get_webpage_text(self, page: Page, n_lines: int = 100) -> str:
        """
        page: playwright page object
        n_lines: number of lines to return from the page innertext
        return: text in the first n_lines of the page
        """
        assert page is not None
        try:
            text_in_viewport = await page.evaluate("""() => {
                return document.body.innerText;
            }""")
            text_in_viewport = "\n".join(text_in_viewport.split("\n")[:n_lines])
            # remove empty lines
            text_in_viewport = "\n".join([line for line in text_in_viewport.split("\n") if line.strip()])
            assert isinstance(text_in_viewport, str)
            return text_in_viewport
        except Exception:
            return ""

    async def get_page_markdown(self, page: Page) -> str:
        # TODO: replace with mdconvert
        assert page is not None
        return await self.get_webpage_text(page, n_lines=1000)
