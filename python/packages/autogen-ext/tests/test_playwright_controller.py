import builtins
from typing import Any

import pytest
from playwright.async_api import async_playwright

from autogen_ext.agents.web_surfer.playwright_controller import PlaywrightController

FAKE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fake Page</title>
</head>
<body>
    <h1 id="header">Welcome to the Fake Page</h1>
    <button id="click-me">Click Me</button>
    <input type="text" id="input-box" />
</body>
</html>
"""


@pytest.mark.asyncio
async def test_playwright_controller_initialization() -> None:
    controller = PlaywrightController()
    assert controller.viewport_width == 1440
    assert controller.viewport_height == 900
    assert controller.animate_actions is False


def test_playwright_controller_reads_page_script_as_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    real_open = builtins.open
    page_script_encodings: list[str | None] = []

    def open_spy(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if str(file).endswith("page_script.js"):
            page_script_encodings.append(kwargs.get("encoding"))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_spy)

    PlaywrightController()

    assert page_script_encodings == ["utf-8"]


@pytest.mark.asyncio
async def test_playwright_controller_visit_page() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(FAKE_HTML)

        controller = PlaywrightController()
        await controller.visit_page(page, "data:text/html," + FAKE_HTML)
        assert page.url.startswith("data:text/html")


@pytest.mark.asyncio
async def test_playwright_controller_click_id() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(FAKE_HTML)

        controller = PlaywrightController()
        rects = await controller.get_interactive_rects(page)
        click_me_id = ""
        for rect in rects:
            if rects[rect]["aria_name"] == "Click Me":
                click_me_id = str(rect)
                break

        await controller.click_id(page, click_me_id)
        assert await page.evaluate("document.activeElement.id") == "click-me"


@pytest.mark.asyncio
async def test_playwright_controller_fill_id() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(FAKE_HTML)
        rects = await PlaywrightController().get_interactive_rects(page)
        input_box_id = ""
        for rect in rects:
            if rects[rect]["tag_name"] == "input, type=text":
                input_box_id = str(rect)
                break
        controller = PlaywrightController()
        await controller.fill_id(page, input_box_id, "test input")
        assert await page.evaluate("document.getElementById('input-box').value") == "test input"
