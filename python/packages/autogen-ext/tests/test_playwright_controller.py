from typing import Any, Dict

import pytest
from autogen_ext.agents.web_surfer.playwright_controller import PlaywrightController
from playwright.async_api import async_playwright

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


def test_playwright_controller_uses_utf8_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure that the page_script.js file is always read using UTF-8 encoding so that
    # non-ASCII content does not trigger UnicodeDecodeError on Windows or other
    # non-UTF-8 default locales.
    import autogen_ext.agents.web_surfer.playwright_controller as pc_mod

    calls: Dict[str, Any] = {}

    import builtins

    real_open = builtins.open  # type: ignore[assignment]

    def fake_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):  # type: ignore[override]
        if isinstance(file, str) and file.endswith("page_script.js") and "r" in mode:
            calls["encoding"] = kwargs.get("encoding")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(pc_mod, "open", fake_open, raising=False)

    pc_mod.PlaywrightController()

    assert calls.get("encoding") == "utf-8"
