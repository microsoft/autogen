import base64
import os
import random
import asyncio
from typing import Any, Dict, Optional, Tuple, Union, cast, Callable
from playwright._impl._errors import Error as PlaywrightError
from playwright._impl._errors import TimeoutError
from playwright.async_api import  Download, Page
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
        viewport_width: int = None,
        viewport_height: int = None,
        _download_handler: Optional[Callable[[Download], None]] = None,
        to_resize_viewport: bool = True,
    ) -> None:
        """
        A controller for Playwright to interact with web pages.
        downloads_folder: folder to save downloaded files
        """
        self.animate_actions = animate_actions
        self.downloads_folder = downloads_folder
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._download_handler = _download_handler
        self.to_resize_viewport = to_resize_viewport
        self._page_script: str = ""

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
        page.on("download", self._download_handler)
        if self.to_resize_viewport:
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

    async def click_id(self, page: Page, identifier: str) -> None:
        """
        Returns new page if a new page is opened, otherwise None.
        """
        # TODO: ADD ANIMATION TO MOVE CURSOR AND HIGHLIGHT THE BOX
        new_page = None
        assert page is not None
        target = page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=100)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Click it
        await target.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)

        box = cast(Dict[str, Union[int, float]], await target.bounding_box())
        
        if self.animate_actions:
            # Scroll into view and highlight the box
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

            # Move cursor to the box slowly
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=30)
            await asyncio.sleep(0.3)

            try:
                # Give it a chance to open a new page
                async with page.expect_event("popup", timeout=1000) as page_info:  # type: ignore
                    await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, delay=10)
                    new_page = await page_info.value  # type: ignore
                    assert isinstance(new_page, Page)
                    await self.on_new_page(new_page)
            except TimeoutError:
                pass

            # Remove the highlight
            await page.evaluate(f"""
                (function() {{
                    let elm = document.querySelector("[__elementId='{identifier}']");
                    if (elm) {{
                        elm.style.border = '';
                    }}
                }})();
            """)
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
        return new_page

    async def fill_id(self, page: Page, identifier: str, value: str) -> None:
        assert page is not None
        target = page.locator(f"[__elementId='{identifier}']")

        # See if it exists
        try:
            await target.wait_for(timeout=300)
        except TimeoutError:
            raise ValueError("No such element.") from None

        # Fill it
        await target.scroll_into_view_if_needed()
        if self.animate_actions:
            # Highlight the box
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
            # Remove the highlight
            await page.evaluate(f"""
                (function() {{
                    let elm = document.querySelector("[__elementId='{identifier}']");
                    if (elm) {{
                        elm.style.border = '';
                    }}
                }})();
            """)

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
        assert page is not None
        """
        page: playwright page object
        n_lines: number of lines to return from the page innertext
        return: text in the first n_lines of the page
        """
        text_in_viewport = await page.evaluate("""() => {
            return document.body.innerText;
        }""")
        text_in_viewport = "\n".join(text_in_viewport.split("\n")[:n_lines])
        # remove empty lines
        text_in_viewport = "\n".join([line for line in text_in_viewport.split("\n") if line.strip()])
