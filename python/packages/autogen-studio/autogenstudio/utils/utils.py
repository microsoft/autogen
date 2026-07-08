import base64
from typing import Sequence

from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
from autogen_core import Image
from autogen_core.models import UserMessage
from loguru import logger


def construct_task(query: str, files: list[dict] | None = None) -> Sequence[ChatMessage]:
    """
    Construct a task from a query string and list of files.
    Returns a list of ChatMessage objects suitable for processing by the agent system.

    Args:
        query: The text query from the user
        files: List of file objects with properties name, content, and type

    Returns:
        List of BaseChatMessage objects (TextMessage, MultiModalMessage)
    """
    if files is None:
        files = []

    messages = []

    # Add the user's text query as a TextMessage
    if query:
        messages.append(TextMessage(source="user", content=query))

    # Process each file based on its type
    for file in files:
        try:
            if file.get("type", "").startswith("image/"):
                # Handle image file using from_base64 method
                # The content is already base64 encoded according to the convertFilesToBase64 function
                image = Image.from_base64(file["content"])
                messages.append(
                    MultiModalMessage(
                        source="user", content=[image], metadata={"filename": file.get("name", "unknown.img")}
                    )
                )
            elif file.get("type", "").startswith("text/"):
                # Handle text file as TextMessage
                text_content = base64.b64decode(file["content"]).decode("utf-8")
                messages.append(
                    TextMessage(
                        source="user", content=text_content, metadata={"filename": file.get("name", "unknown.txt")}
                    )
                )
            else:
                # Log unsupported file types but still try to process based on best guess
                logger.warning(f"Potentially unsupported file type: {file.get('type')} for file {file.get('name')}")
                if file.get("type", "").startswith("application/"):
                    # Try to treat as text if it's an application type (like JSON)
                    text_content = base64.b64decode(file["content"]).decode("utf-8")
                    messages.append(
                        TextMessage(
                            source="user",
                            content=text_content,
                            metadata={
                                "filename": file.get("name", "unknown.file"),
                                "filetype": file.get("type", "unknown"),
                            },
                        )
                    )
        except Exception as e:
            logger.error(f"Error processing file {file.get('name')}: {str(e)}")
            # Continue processing other files even if one fails

    return messages
