import asyncio
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_ext.agents import MultimodalWebSurfer
from playwright.async_api import async_playwright  # Add this import

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")

    web_surfer = MultimodalWebSurfer(
        name="web_surfer",
        model_client=model_client,
        headless=False,
        debug_dir="logs",
        downloads_folder="logs",
        to_save_screenshots=True,
        use_ocr=False
    )



    while True:
        # Run the team and stream messages
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, ">: ")
        response = await web_surfer.run(user_input)
        print(response)


asyncio.run(main())


"""
Change log:




TO FIX:
- chromium browser in headful mode does not resize properly
"""
