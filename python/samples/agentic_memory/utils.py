from typing import Any, Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient


def create_oai_client(config: Dict[str, Any]) -> ChatCompletionClient:
    """
    Creates a chat completion client from OpenAI.
    """
    client = OpenAIChatCompletionClient(
        model=config["model"],
        max_tokens=config["max_completion_tokens"],
        max_retries=config["max_retries"],
        temperature=config["temperature"],
        presence_penalty=config["presence_penalty"],
        frequency_penalty=config["frequency_penalty"],
        top_p=config["top_p"],
    )
    return client


def load_yaml_file(file_path: str) -> Any:
    """
    Opens a file and returns its contents.
    """
    with open(file_path, "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)

