import os
import json
from typing import List, Optional, Dict, Set, Union
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
    exclude: Optional[str] = None,
) -> List[Dict]:
    """Get a list of configs for openai + azure openai api calls.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the openai api key.
        aoai_api_key_file (str, optional): The file name of the azure openai api key.
        aoai_api_base_file (str, optional): The file name of the azure openai api base.
        exclude (str, optional): The api type to exclude, "openai" or "aoai".

    Returns:
        list: A list of configs for openai api calls.
    """
    if "OPENAI_API_KEY" not in os.environ and exclude != "openai":
        try:
            with open(f"{key_file_path}/{openai_api_key_file}") as key_file:
                os.environ["OPENAI_API_KEY"] = key_file.read().strip()
        except FileNotFoundError:
            logging.info(
                "To use OpenAI API, please set OPENAI_API_KEY in os.environ "
                "or create key_openai.txt in the specified path, or specify the api_key in config_list."
            )
    if "AZURE_OPENAI_API_KEY" not in os.environ and exclude != "aoai":
        try:
            with open(f"{key_file_path}/{aoai_api_key_file}") as key_file:
                os.environ["AZURE_OPENAI_API_KEY"] = key_file.read().strip()
        except FileNotFoundError:
            logging.info(
                "To use Azure OpenAI API, please set AZURE_OPENAI_API_KEY in os.environ "
                "or create key_aoai.txt in the specified path, or specify the api_key in config_list."
            )
    if "AZURE_OPENAI_API_BASE" not in os.environ and exclude != "aoai":
        try:
            with open(f"{key_file_path}/{aoai_api_base_file}") as key_file:
                os.environ["AZURE_OPENAI_API_BASE"] = key_file.read().strip()
        except FileNotFoundError:
            logging.info(
                "To use Azure OpenAI API, please set AZURE_OPENAI_API_BASE in os.environ "
                "or create base_aoai.txt in the specified path, or specify the api_base in config_list."
            )
    aoai_config = (
        get_config_list(
            # Assuming Azure OpenAI api keys in os.environ["AZURE_OPENAI_API_KEY"], in separated lines
            api_keys=os.environ.get("AZURE_OPENAI_API_KEY", "").split("\n"),
            # Assuming Azure OpenAI api bases in os.environ["AZURE_OPENAI_API_BASE"], in separated lines
            api_bases=os.environ.get("AZURE_OPENAI_API_BASE", "").split("\n"),
            api_type="azure",
            api_version="2023-06-01-preview",  # change if necessary
        )
        if exclude != "aoai"
        else []
    )
    openai_config = (
        get_config_list(
            # Assuming OpenAI API_KEY in os.environ["OPENAI_API_KEY"]
            api_keys=os.environ.get("OPENAI_API_KEY", "").split("\n"),
            # "api_type": "open_ai",
            # "api_base": "https://api.openai.com/v1",
        )
        if exclude != "openai"
        else []
    )
    config_list = openai_config + aoai_config
    return config_list


def config_list_from_models(
    key_file_path: Optional[str] = ".",
    openai_api_key_file: Optional[str] = "key_openai.txt",
    aoai_api_key_file: Optional[str] = "key_aoai.txt",
    aoai_api_base_file: Optional[str] = "base_aoai.txt",
    exclude: Optional[str] = None,
    model_list: Optional[list] = None,
) -> List[Dict]:
    """Get a list of configs for api calls with models in the model list.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the openai api key.
        aoai_api_key_file (str, optional): The file name of the azure openai api key.
        aoai_api_base_file (str, optional): The file name of the azure openai api base.
        exclude (str, optional): The api type to exclude, "openai" or "aoai".
        model_list (list, optional): The model list.

    Returns:
        list: A list of configs for openai api calls.
    """
    config_list = config_list_openai_aoai(
        key_file_path,
        openai_api_key_file,
        aoai_api_key_file,
        aoai_api_base_file,
        exclude,
    )
    if model_list:
        config_list = [{**config, "model": model} for model in model_list for config in config_list]
    return config_list


def config_list_gpt4_gpt35(
    key_file_path: Optional[str] = ".",
    openai_api_key_file: Optional[str] = "key_openai.txt",
    aoai_api_key_file: Optional[str] = "key_aoai.txt",
    aoai_api_base_file: Optional[str] = "base_aoai.txt",
    exclude: Optional[str] = None,
) -> List[Dict]:
    """Get a list of configs for gpt-4 followed by gpt-3.5 api calls.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the openai api key.
        aoai_api_key_file (str, optional): The file name of the azure openai api key.
        aoai_api_base_file (str, optional): The file name of the azure openai api base.
        exclude (str, optional): The api type to exclude, "openai" or "aoai".

    Returns:
        list: A list of configs for openai api calls.
    """
    return config_list_from_models(
        key_file_path,
        openai_api_key_file,
        aoai_api_key_file,
        aoai_api_base_file,
        exclude,
        model_list=["gpt-4", "gpt-3.5-turbo"],
    )


def filter_config(config_list, filter_dict):
    """Filter the config list by provider and model.

    Args:
        config_list (list): The config list.
        filter_dict (dict, optional): The filter dict with keys corresponding to a field in each config,
            and values corresponding to lists of acceptable values for each key.

    Returns:
        list: The filtered config list.
    """
    if filter_dict:
        config_list = [
            config for config in config_list if all(config.get(key) in value for key, value in filter_dict.items())
        ]
    return config_list


def config_list_from_json(
    env_or_file: str,
    file_location: Optional[str] = "",
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]], Set[Union[str, None]]]]] = None,
) -> List[Dict]:
    """Get a list of configs from a json parsed from an env variable or a file.

    Args:
        env_or_file (str): The env variable name or file name.
        file_location (str, optional): The file location.
        filter_dict (dict, optional): The filter dict with keys corresponding to a field in each config,
            and values corresponding to lists of acceptable values for each key.
            e.g.,
    ```python
    filter_dict = {
        "api_type": ["open_ai", None],  # None means a missing key is acceptable
        "model": ["gpt-3.5-turbo", "gpt-4"],
    }
    ```

    Returns:
        list: A list of configs for openai api calls.
    """
    json_str = os.environ.get(env_or_file)
    if json_str:
        config_list = json.loads(json_str)
    else:
        try:
            with open(os.path.join(file_location, env_or_file)) as json_file:
                config_list = json.load(json_file)
        except FileNotFoundError:
            return []
    return filter_config(config_list, filter_dict)
