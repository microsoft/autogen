from typing import Any, Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient


def create_oai_client(settings: Dict[str, Any]) -> ChatCompletionClient:
    """
    Creates a chat completion client from OpenAI.
    """
    client = OpenAIChatCompletionClient(
        model=settings["model"],
        max_tokens=settings["max_completion_tokens"],
        max_retries=settings["max_retries"],
        temperature=settings["temperature"],
        presence_penalty=settings["presence_penalty"],
        frequency_penalty=settings["frequency_penalty"],
        top_p=settings["top_p"],
    )
    return client


def load_yaml_file(file_path: str) -> Any:
    """
    Opens a file and returns its contents.
    """
    with open(file_path, "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)

