from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient


def create_oai_client(settings, logger) -> ChatCompletionClient:
    """
    Creates a chat completion client from OpenAI.
    """
    logger.enter_function()
    args = {}
    args["model"] = settings["model"]
    args["max_completion_tokens"] = settings["max_completion_tokens"]
    args["max_retries"] = settings["max_retries"]
    if not args["model"].startswith("o1"):
        args["temperature"] = settings["temperature"]
        args["presence_penalty"] = settings["presence_penalty"]
        args["frequency_penalty"] = settings["frequency_penalty"]
        args["top_p"] = settings["top_p"]
    if "api_key" in settings:
        args["api_key"] = settings["api_key"]

    # Instantiate the client.
    client = OpenAIChatCompletionClient(**args)

    # Log some details.
    logger.info("Client:  {}".format(client._resolved_model))
    logger.info("  created through OpenAI")
    logger.leave_function()
    return client
