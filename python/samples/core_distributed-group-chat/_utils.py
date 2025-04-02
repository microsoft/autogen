import logging
import os
from typing import Any, Iterable, Type

import yaml
from _types import AppConfig
from autogen_core import MessageSerializer, try_get_known_serializers_for_type
from autogen_ext.models.openai.config import AzureOpenAIClientConfiguration
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def load_config(file_path: str = os.path.join(os.path.dirname(__file__), "config.yaml")) -> AppConfig:
    model_client = {}
    with open(file_path, "r") as file:
        config_data = yaml.safe_load(file)
        model_client = config_data["client_config"]
        del config_data["client_config"]
        app_config = AppConfig(**config_data)
    # This was required as it couldn't automatically instantiate AzureOpenAIClientConfiguration

    aad_params = {}
    if len(model_client.get("api_key", "")) == 0:
        aad_params["azure_ad_token_provider"] = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )

    app_config.client_config = AzureOpenAIClientConfiguration(**model_client, **aad_params)  # type: ignore[typeddict-item]
    return app_config


def get_serializers(types: Iterable[Type[Any]]) -> list[MessageSerializer[Any]]:
    serializers = []
    for type in types:
        serializers.extend(try_get_known_serializers_for_type(type))  # type: ignore
    return serializers  # type: ignore [reportUnknownVariableType]


# TODO: This is a helper function to get rid of a lot of logs until we find exact loggers to properly set log levels ...
def set_all_log_levels(log_leve: int):
    # Iterate through all existing loggers and set their levels
    for _, logger in logging.root.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):  # Ensure it's actually a Logger object
            logger.setLevel(log_leve)  # Adjust to DEBUG or another level as needed
