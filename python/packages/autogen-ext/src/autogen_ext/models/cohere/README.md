# Cohere Chat Completion Client - Usage Examples

## Installation

```bash
pip install "autogen-ext[cohere]"
```

## Basic Usage

```python
import asyncio
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


async def main():
    client = CohereChatCompletionClient(
        model="command-r-plus-08-2024",
        api_key="your-api-key",  # or use the environment variable COHERE_API_KEY
    )
    
    result = await client.create(
        [UserMessage(content="What is the capital of France?", source="user")]
    )
    print(result.content)


asyncio.run(main())
```

## Example of Tool Invocation

```python
import asyncio
from autogen_core.models import UserMessage
from autogen_core.tools import FunctionTool
from autogen_ext.models.cohere import CohereChatCompletionClient


def get_weather(location: str) -> str:
    """Get the weather for a location."""
    return f"The weather in {location} is sunny and 72°F."


async def main():
    client = CohereChatCompletionClient(
        model="command-r-plus-08-2024",
        api_key="your-api-key",
    )
    
    weather_tool = FunctionTool(
        get_weather,
        description="Get the current weather for a location",
        name="get_weather",
    )
    
    result = await client.create(
        messages=[UserMessage(content="What's the weather like in Tokyo?", source="user")],
        tools=[weather_tool],
    )
    
    if isinstance(result.content, list):
        for tool_call in result.content:
            print(f"Tool: {tool_call.name}")
            print(f"Arguments: {tool_call.arguments}")


asyncio.run(main())
```

## Examples of Streaming Usage

```python
import asyncio
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


async def main():
    client = CohereChatCompletionClient(
        model="command-r-plus-08-2024",
        api_key="your-api-key",
    )
    
    async for chunk in client.create_stream(
        [UserMessage(content="Tell me a short story.", source="user")]
    ):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True)
        else:
            # Final chunk（CreateResult）
            print(f"\n\nTokens used: {chunk.usage.total_tokens}")


asyncio.run(main())
```

## Example of Using JSON Output Mode

```python
import asyncio
from pydantic import BaseModel
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


class Person(BaseModel):
    name: str
    age: int
    city: str


async def main():
    client = CohereChatCompletionClient(
        model="command-r-plus-08-2024",
        api_key="your-api-key",
    )
    
    result = await client.create(
        messages=[
            UserMessage(
                content="Extract the person info: John Doe is 30 years old and lives in New York.",
                source="user",
            )
        ],
        json_output=Person,
    )
    
    print(result.content)


asyncio.run(main())
```

## Timeout and Retry Settings

For requests that run for extended periods, you can configure timeouts and retries:

```python
import asyncio
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


async def main():
    client = CohereChatCompletionClient(
        model="command-r-plus-08-2024",
        api_key="your-api-key",
        timeout=180.0,  # 3 minute timeout
        max_retries=3,  # Up to 3 retries
    )
    
    result = await client.create(
        [UserMessage(content="Tell me a long story about AI.", source="user")]
    )
    print(result.content)


asyncio.run(main())
```

By default, the timeout is set to 120 seconds.

## Examples of Vision Model Usage

**Important Notes:**
- The Vision Model does not currently support tool calls.
- If a tool is specified, it will be automatically ignored and a warning log will be output.

```python
import asyncio
from PIL import Image as PILImage
from autogen_core import Image
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


async def main():
    client = CohereChatCompletionClient(
        model="command-a-vision-07-2025",
        api_key="your-api-key",
    )
    
    # Load from image file
    pil_image = PILImage.open("path/to/image.jpg")
    image = Image.from_pil(pil_image)
    
    # or created from base64
    # image = Image.from_base64("base64_encoded_string")
    
    # Create a multimodal message
    result = await client.create(
        [UserMessage(
            content=[
                "Please describe this image.",
                image
            ],
            source="user"
        )]
    )
    print(result.content)


asyncio.run(main())
```

### Handling multiple images

```python
import asyncio
from PIL import Image as PILImage
from autogen_core import Image
from autogen_core.models import UserMessage
from autogen_ext.models.cohere import CohereChatCompletionClient


async def main():
    client = CohereChatCompletionClient(
        model="takane-vision-prerelease-10-2025",
        api_key="your-api-key",
    )
    
    #  Prepare multiple images
    image1 = Image.from_pil(PILImage.open("image1.jpg"))
    image2 = Image.from_pil(PILImage.open("image2.jpg"))
    
    # A message containing multiple images and text
    result = await client.create(
        [UserMessage(
            content=[
                "Please compare these two images.:",
                image1,
                image2
            ],
            source="user"
        )]
    )
    print(result.content)


asyncio.run(main())
```


For more details, see the [Cohere documentation](https://docs.cohere.com/docs/models).
