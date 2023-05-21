import os
import json
from typing import List, Optional, Dict
import logging

NON_CACHE_KEY = ["api_key", "api_base", "api_type", "api_version"]


def get_key(config):
    """Get a unique identifier of a configuration.

    Args:
        config (dict or list): A configuration.

    Returns:
        tuple: A unique identifier which can be used as a key for a dict.
    """
    copied = False
    for key in NON_CACHE_KEY:
        if key in config:
            config, copied = config.copy() if not copied else config, True
            config.pop(key)
    # if isinstance(config, dict):
    #     return tuple(get_key(x) for x in sorted(config.items()))
    # if isinstance(config, list):
    #     return tuple(get_key(x) for x in config)
    # return config
    return json.dumps(config, sort_keys=True)


def get_config_list(
    api_keys: List, api_bases: Optional[List] = None, api_type: Optional[str] = None, api_version: Optional[str] = None
) -> List[Dict]:
    """Get a list of configs for openai api calls.

    Args:
        api_keys (list): The api keys for openai api calls.
        api_bases (list, optional): The api bases for openai api calls.
        api_type (str, optional): The api type for openai api calls.
        api_version (str, optional): The api version for openai api calls.
    """
    config_list = []
    for i, api_key in enumerate(api_keys):
        if not api_key.strip():
            continue
        config = {"api_key": api_key}
        if api_bases:
            config["api_base"] = api_bases[i]
        if api_type:
            config["api_type"] = api_type
        if api_version:
            config["api_version"] = api_version
        config_list.append(config)
    return config_list


def config_list_openai_aoai(
    key_file_path: Optional[str] = ".",
    openai_api_key_file: Optional[str] = "key_openai.txt",
    aoai_api_key_file: Optional[str] = "key_aoai.txt",
    aoai_api_base_file: Optional[str] = "base_aoai.txt",
) -> List[Dict]:
    """Get a list of configs for openai + azure openai api calls.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the openai api key.
        aoai_api_key_file (str, optional): The file name of the azure openai api key.
        aoai_api_base_file (str, optional): The file name of the azure openai api base.

    Returns:
        list: A list of configs for openai api calls.
    """
    if "OPENAI_API_KEY" not in os.environ:
        try:
            os.environ["OPENAI_API_KEY"] = open(f"{key_file_path}/{openai_api_key_file}").read().strip()
        except FileNotFoundError:
            logging.info(
                "To use OpenAI API, please set OPENAI_API_KEY in os.environ "
                "or create key_openai.txt in the specified path, or specify the api_key in config_list."
            )
    if "AZURE_OPENAI_API_KEY" not in os.environ:
        try:
            os.environ["AZURE_OPENAI_API_KEY"] = open(f"{key_file_path}/{aoai_api_key_file}").read().strip()
        except FileNotFoundError:
            logging.info(
                "To use Azure OpenAI API, please set AZURE_OPENAI_API_KEY in os.environ "
                "or create key_aoai.txt in the specified path, or specify the api_key in config_list."
            )
    if "AZURE_OPENAI_API_BASE" not in os.environ:
        try:
            os.environ["AZURE_OPENAI_API_BASE"] = open(f"{key_file_path}/{aoai_api_base_file}").read().strip()
        except FileNotFoundError:
            logging.info(
                "To use Azure OpenAI API, please set AZURE_OPENAI_API_BASE in os.environ "
                "or create base_aoai.txt in the specified path, or specify the api_base in config_list."
            )
    aoai_config = get_config_list(
        # Assuming Azure OpenAI api keys in os.environ["AZURE_OPENAI_API_KEY"], in separated lines
        api_keys=os.environ.get("AZURE_OPENAI_API_KEY", "").split("\n"),
        # Assuming Azure OpenAI api bases in os.environ["AZURE_OPENAI_API_BASE"], in separated lines
        api_bases=os.environ.get("AZURE_OPENAI_API_BASE", "").split("\n"),
        api_type="azure",
        api_version="2023-03-15-preview",  # change if necessary
    )
    openai_config = get_config_list(
        # Assuming OpenAI API_KEY in os.environ["OPENAI_API_KEY"]
        api_keys=os.environ.get("OPENAI_API_KEY", "").split("\n"),
        # "api_type": "open_ai",
        # "api_base": "https://api.openai.com/v1",
    )
    config_list = openai_config + aoai_config
    return config_list


def config_list_gpt4_gpt35(
    key_file_path: Optional[str] = ".",
    openai_api_key_file: Optional[str] = "key_openai.txt",
    aoai_api_key_file: Optional[str] = "key_aoai.txt",
    aoai_api_base_file: Optional[str] = "base_aoai.txt",
) -> List[Dict]:
    """Get a list of configs for gpt-4 followed by gpt-3.5 api calls.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the openai api key.
        aoai_api_key_file (str, optional): The file name of the azure openai api key.
        aoai_api_base_file (str, optional): The file name of the azure openai api base.

    Returns:
        list: A list of configs for openai api calls.
    """

    config_list = config_list_openai_aoai(
        key_file_path,
        openai_api_key_file,
        aoai_api_key_file,
        aoai_api_base_file,
    )
    return [{**config, "model": "gpt-4"} for config in config_list] + [
        {**config, "model": "gpt-3.5-turbo"} for config in config_list
    ]
