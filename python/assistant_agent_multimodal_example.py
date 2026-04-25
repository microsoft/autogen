import asyncio
from io import BytesIO
import PIL
import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import Image

async def main():
    # Create the agent (using GPT-4o for multi-modal support)
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
    )
    # Create a multi-modal message with random image and text.
    pil_image = PIL.Image.open(BytesIO(requests.get("https://picsum.photos/300/200").content))
    img = Image(pil_image)
    multi_modal_message = MultiModalMessage(content=["Can you describe the content of this image?", img], source="user")
    result = await agent.run(task=multi_modal_message)
    print(result.messages[-1].content)  # type: ignore
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
