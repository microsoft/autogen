import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Set, Union
import logging
from dotenv import find_dotenv, load_dotenv


NON_CACHE_KEY = ["api_key", "base_url", "api_type", "api_version"]


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
    api_keys: List, base_urls: Optional[List] = None, api_type: Optional[str] = None, api_version: Optional[str] = None
) -> List[Dict]:
    """Get a list of configs for openai api calls.

    Args:
        api_keys (list): The api keys for openai api calls.
        base_urls (list, optional): The api bases for openai api calls.
        api_type (str, optional): The api type for openai api calls.
        api_version (str, optional): The api version for openai api calls.
    """
    config_list = []
    for i, api_key in enumerate(api_keys):
        if not api_key.strip():
            continue
        config = {"api_key": api_key}
        if base_urls:
            config["base_url"] = base_urls[i]
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
                "OPENAI_API_KEY is not found in os.environ "
                "and key_openai.txt is not found in the specified path. You can specify the api_key in the config_list."
            )
    if "AZURE_OPENAI_API_KEY" not in os.environ and exclude != "aoai":
        try:
            with open(f"{key_file_path}/{aoai_api_key_file}") as key_file:
                os.environ["AZURE_OPENAI_API_KEY"] = key_file.read().strip()
        except FileNotFoundError:
            logging.info(
                "AZURE_OPENAI_API_KEY is not found in os.environ "
                "and key_aoai.txt is not found in the specified path. You can specify the api_key in the config_list."
            )
    if "AZURE_OPENAI_API_BASE" not in os.environ and exclude != "aoai":
        try:
            with open(f"{key_file_path}/{aoai_api_base_file}") as key_file:
                os.environ["AZURE_OPENAI_API_BASE"] = key_file.read().strip()
        except FileNotFoundError:
            logging.info(
                "AZURE_OPENAI_API_BASE is not found in os.environ "
                "and base_aoai.txt is not found in the specified path. You can specify the base_url in the config_list."
            )
    aoai_config = (
        get_config_list(
            # Assuming Azure OpenAI api keys in os.environ["AZURE_OPENAI_API_KEY"], in separated lines
            api_keys=os.environ.get("AZURE_OPENAI_API_KEY", "").split("\n"),
            # Assuming Azure OpenAI api bases in os.environ["AZURE_OPENAI_API_BASE"], in separated lines
            base_urls=os.environ.get("AZURE_OPENAI_API_BASE", "").split("\n"),
            api_type="azure",
            api_version="2023-08-01-preview",  # change if necessary
        )
        if exclude != "aoai"
        else []
    )
    openai_config = (
        get_config_list(
            # Assuming OpenAI API_KEY in os.environ["OPENAI_API_KEY"]
            api_keys=os.environ.get("OPENAI_API_KEY", "").split("\n"),
            # "api_type": "open_ai",
            # "base_url": "https://api.openai.com/v1",
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
        config_list_path = os.path.join(file_location, env_or_file)
        try:
            with open(config_list_path) as json_file:
                config_list = json.load(json_file)
        except FileNotFoundError:
            logging.warning(f"The specified config_list file '{config_list_path}' does not exist.")
            return []
    return filter_config(config_list, filter_dict)


def get_config(
    api_key: str, base_url: Optional[str] = None, api_type: Optional[str] = None, api_version: Optional[str] = None
) -> Dict:
    """
    Construct a configuration dictionary with the provided API configurations.
    Appending the additional configurations to the config only if they're set

    example:
    >> model_api_key_map={
        "gpt-4": "OPENAI_API_KEY",
        "gpt-3.5-turbo": {
            "api_key_env_var": "ANOTHER_API_KEY",
            "api_type": "aoai",
            "api_version": "v2",
            "base_url": "https://api.someotherapi.com"
        }
    }
    Args:
        api_key (str): The API key used for authenticating API requests.
        base_url (str, optional): The base URL of the API. Defaults to None.
        api_type (str, optional): The type or kind of API. Defaults to None.
        api_version (str, optional): The API version. Defaults to None.

    Returns:
        Dict: A dictionary containing the API configurations.
    """
    config = {"api_key": api_key}
    if base_url:
        config["base_url"] = base_url
    if api_type:
        config["api_type"] = api_type
    if api_version:
        config["api_version"] = api_version
    return config


def config_list_from_dotenv(
    dotenv_file_path: Optional[str] = None, model_api_key_map: Optional[dict] = None, filter_dict: Optional[dict] = None
) -> List[Dict[str, Union[str, Set[str]]]]:
    """
    Load API configurations from a specified .env file or environment variables and construct a list of configurations.

    This function will:
    - Load API keys from a provided .env file or from existing environment variables.
    - Create a configuration dictionary for each model using the API keys and additional configurations.
    - Filter and return the configurations based on provided filters.

    model_api_key_map will default to `{"gpt-4": "OPENAI_API_KEY", "gpt-3.5-turbo": "OPENAI_API_KEY"}` if none

    Args:
        dotenv_file_path (str, optional): The path to the .env file. Defaults to None.
        model_api_key_map (str/dict, optional): A dictionary mapping models to their API key configurations.
                                           If a string is provided as configuration, it is considered as an environment
                                           variable name storing the API key.
                                           If a dict is provided, it should contain at least 'api_key_env_var' key,
                                           and optionally other API configurations like 'base_url', 'api_type', and 'api_version'.
                                           Defaults to a basic map with 'gpt-4' and 'gpt-3.5-turbo' mapped to 'OPENAI_API_KEY'.
        filter_dict (dict, optional): A dictionary containing the models to be loaded.
                                      Containing a 'model' key mapped to a set of model names to be loaded.
                                      Defaults to None, which loads all found configurations.

    Returns:
        List[Dict[str, Union[str, Set[str]]]]: A list of configuration dictionaries for each model.

    Raises:
        FileNotFoundError: If the specified .env file does not exist.
        TypeError: If an unsupported type of configuration is provided in model_api_key_map.
    """
    if dotenv_file_path:
        dotenv_path = Path(dotenv_file_path)
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
        else:
            logging.warning(f"The specified .env file {dotenv_path} does not exist.")
    else:
        dotenv_path = find_dotenv()
        if not dotenv_path:
            logging.warning("No .env file found. Loading configurations from environment variables.")
        load_dotenv(dotenv_path)

    # Ensure the model_api_key_map is not None to prevent TypeErrors during key assignment.
    model_api_key_map = model_api_key_map or {}

    # Ensure default models are always considered
    default_models = ["gpt-4", "gpt-3.5-turbo"]

    for model in default_models:
        # Only assign default API key if the model is not present in the map.
        # If model is present but set to invalid/empty, do not overwrite.
        if model not in model_api_key_map:
            model_api_key_map[model] = "OPENAI_API_KEY"

    env_var = []
    # Loop over the models and create configuration dictionaries
    for model, config in model_api_key_map.items():
        if isinstance(config, str):
            api_key_env_var = config
            config_dict = get_config(api_key=os.getenv(api_key_env_var))
        elif isinstance(config, dict):
            api_key = os.getenv(config.get("api_key_env_var", "OPENAI_API_KEY"))
            config_without_key_var = {k: v for k, v in config.items() if k != "api_key_env_var"}
            config_dict = get_config(api_key=api_key, **config_without_key_var)
        else:
            logging.warning(f"Unsupported type {type(config)} for model {model} configuration")

        if not config_dict["api_key"] or config_dict["api_key"].strip() == "":
            logging.warning(
                f"API key not found or empty for model {model}. Please ensure path to .env file is correct."
            )
            continue  # Skip this configuration and continue with the next

        # Add model to the configuration and append to the list
        config_dict["model"] = model
        env_var.append(config_dict)

    fd, temp_name = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w+") as temp:
            env_var_str = json.dumps(env_var)
            temp.write(env_var_str)
            temp.flush()

            # Assuming config_list_from_json is a valid function from your code
            config_list = config_list_from_json(env_or_file=temp_name, filter_dict=filter_dict)
    finally:
        # The file is deleted after using its name (to prevent windows build from breaking)
        os.remove(temp_name)

    if len(config_list) == 0:
        logging.error("No configurations loaded.")
        return []

    logging.info(f"Models available: {[config['model'] for config in config_list]}")
    return config_list


def retrieve_assistants_by_name(client, name) -> str:
    """
    Return the assistants with the given name from OAI assistant API
    """
    assistants = client.beta.assistants.list()
    candidate_assistants = []
    for assistant in assistants.data:
        if assistant.name == name:
            candidate_assistants.append(assistant)
    return candidate_assistants
