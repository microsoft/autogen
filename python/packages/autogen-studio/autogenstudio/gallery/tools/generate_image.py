import base64
import io
import uuid
from pathlib import Path
from typing import List, Literal, Optional

from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from openai import OpenAI
from PIL import Image


async def generate_image(
    query: str,
    output_dir: Optional[Path] = None,
    image_size: Literal["1024x1024", "1024x1536", "1536x1024"] = "1024x1024",
) -> List[str]:
    """
    Generate images using OpenAI's GPT Image 2 model based on a text description.

    Args:
        query: Natural language description of the desired image
        output_dir: Directory to save generated images (default: current directory)
        image_size: Size of generated image (1024x1024, 1024x1536, or 1536x1024)

    Returns:
        List[str]: Paths to the generated image files
    """
    # Initialize the OpenAI client
    client = OpenAI()

    # GPT Image models always return base64-encoded image data.
    response = client.images.generate(model="gpt-image-2", prompt=query, n=1, size=image_size)

    saved_files = []

    # Process the response
    if response.data:
        for image_data in response.data:
            # Generate a unique filename
            file_name: str = f"{uuid.uuid4()}.png"

            # Use output_dir if provided, otherwise use current directory
            file_path = Path(output_dir) / file_name if output_dir else Path(file_name)

            base64_str = image_data.b64_json
            if base64_str:
                img = Image.open(io.BytesIO(base64.decodebytes(bytes(base64_str, "utf-8"))))
                # Save the image to a file
                img.save(file_path)
                saved_files.append(str(file_path))

    return saved_files


# Create the image generation tool
generate_image_tool = FunctionTool(
    func=generate_image,
    description="Generate images using GPT Image 2 based on text descriptions.",
    global_imports=[
        "io",
        "uuid",
        "base64",
        ImportFromModule("typing", ("List", "Optional", "Literal")),
        ImportFromModule("pathlib", ("Path",)),
        ImportFromModule("openai", ("OpenAI",)),
        ImportFromModule("PIL", ("Image",)),
    ],
)
