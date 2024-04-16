import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from openai.types.beta.assistant import Assistant

NON_CACHE_KEY = ["api_key", "base_url", "api_type", "api_version"]
DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"
OAI_PRICE1K = {
    # https://openai.com/pricing
    # gpt-4-turbo
    "gpt-4-0125-preview": (0.01, 0.03),
    "gpt-4-1106-preview": (0.01, 0.03),
    "gpt-4-1106-vision-preview": (0.01, 0.03),  # TODO: support vision pricing of images
    # gpt-4
    "gpt-4": (0.03, 0.06),
    "gpt-4-32k": (0.06, 0.12),
    # gpt-3.5 turbo
    "gpt-3.5-turbo": (0.0005, 0.0015),  # default is 0125
    "gpt-3.5-turbo-0125": (0.0005, 0.0015),  # 16k
    "gpt-3.5-turbo-instruct": (0.0015, 0.002),
    # base model
    "davinci-002": 0.002,
    "babbage-002": 0.0004,
    # old model
    "gpt-3.5-turbo-1106": (0.001, 0.002),
    "gpt-3.5-turbo-0613": (0.0015, 0.002),
    # "gpt-3.5-turbo-16k": (0.003, 0.004),
    "gpt-3.5-turbo-16k-0613": (0.003, 0.004),
    "gpt-3.5-turbo-0301": (0.0015, 0.002),
    "text-ada-001": 0.0004,
    "text-babbage-001": 0.0005,
    "text-curie-001": 0.002,
    "code-cushman-001": 0.024,
    "code-davinci-002": 0.1,
    "text-davinci-002": 0.02,
    "text-davinci-003": 0.02,
    "gpt-4-0314": (0.03, 0.06),  # deprecate in Sep
    "gpt-4-32k-0314": (0.06, 0.12),  # deprecate in Sep
    "gpt-4-0613": (0.03, 0.06),
    "gpt-4-32k-0613": (0.06, 0.12),
    "gpt-4-turbo-preview": (0.01, 0.03),
    # https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/#pricing
    "gpt-35-turbo": (0.0005, 0.0015),  # what's the default? using 0125 here.
    "gpt-35-turbo-0125": (0.0005, 0.0015),
    "gpt-35-turbo-instruct": (0.0015, 0.002),
    "gpt-35-turbo-1106": (0.001, 0.002),
    "gpt-35-turbo-0613": (0.0015, 0.002),
    "gpt-35-turbo-0301": (0.0015, 0.002),
    "gpt-35-turbo-16k": (0.003, 0.004),
    "gpt-35-turbo-16k-0613": (0.003, 0.004),
}


def get_key(config: Dict[str, Any]) -> str:
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


def is_valid_api_key(api_key: str) -> bool:
    """Determine if input is valid OpenAI API key.

    Args:
        api_key (str): An input string to be validated.

    Returns:
        bool: A boolean that indicates if input is valid OpenAI API key.
    """
    api_key_re = re.compile(r"^sk-[A-Za-z0-9]{32,}$")
    return bool(re.fullmatch(api_key_re, api_key))


def get_config_list(
    api_keys: List[str],
    base_urls: Optional[List[str]] = None,
    api_type: Optional[str] = None,
    api_version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get a list of configs for OpenAI API client.

    Args:
        api_keys (list): The api keys for openai api calls.
        base_urls (list, optional): The api bases for openai api calls. If provided, should match the length of api_keys.
        api_type (str, optional): The api type for openai api calls.
        api_version (str, optional): The api version for openai api calls.

    Returns:
        list: A list of configs for OepnAI API calls.

    Example:
    ```python
    # Define a list of API keys
    api_keys = ['key1', 'key2', 'key3']

    # Optionally, define a list of base URLs corresponding to each API key
    base_urls = ['https://api.service1.com', 'https://api.service2.com', 'https://api.service3.com']

    # Optionally, define the API type and version if they are common for all keys
    api_type = 'azure'
    api_version = '2024-02-15-preview'

    # Call the get_config_list function to get a list of configuration dictionaries
    config_list = get_config_list(api_keys, base_urls, api_type, api_version)
    ```

    """
    if base_urls is not None:
        assert len(api_keys) == len(base_urls), "The length of api_keys must match the length of base_urls"
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
    openai_api_base_file: Optional[str] = "base_openai.txt",
    aoai_api_base_file: Optional[str] = "base_aoai.txt",
    exclude: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get a list of configs for OpenAI API client (including Azure or local model deployments that support OpenAI's chat completion API).

    This function constructs configurations by reading API keys and base URLs from environment variables or text files.
    It supports configurations for both OpenAI and Azure OpenAI services, allowing for the exclusion of one or the other.
    When text files are used, the environment variables will be overwritten.
    To prevent text files from being used, set the corresponding file name to None.
    Or set key_file_path to None to disallow reading from text files.

    Args:
        key_file_path (str, optional): The directory path where the API key files are located. Defaults to the current directory.
        openai_api_key_file (str, optional): The filename containing the OpenAI API key. Defaults to 'key_openai.txt'.
        aoai_api_key_file (str, optional): The filename containing the Azure OpenAI API key. Defaults to 'key_aoai.txt'.
        openai_api_base_file (str, optional): The filename containing the OpenAI API base URL. Defaults to 'base_openai.txt'.
        aoai_api_base_file (str, optional): The filename containing the Azure OpenAI API base URL. Defaults to 'base_aoai.txt'.
        exclude (str, optional): The API type to exclude from the configuration list. Can be 'openai' or 'aoai'. Defaults to None.

    Returns:
        List[Dict]: A list of configuration dictionaries. Each dictionary contains keys for 'api_key',
            and optionally 'base_url', 'api_type', and 'api_version'.

    Raises:
        FileNotFoundError: If the specified key files are not found and the corresponding API key is not set in the environment variables.

    Example:
        # To generate configurations excluding Azure OpenAI:
        configs = config_list_openai_aoai(exclude='aoai')

    File samples:
        - key_aoai.txt

        ```
        aoai-12345abcdef67890ghijklmnopqr
        aoai-09876zyxwvuts54321fedcba
        ```

        - base_aoai.txt

        ```
        https://api.azure.com/v1
        https://api.azure2.com/v1
        ```

    Notes:
        - The function checks for API keys and base URLs in the following environment variables: 'OPENAI_API_KEY', 'AZURE_OPENAI_API_KEY',
          'OPENAI_API_BASE' and 'AZURE_OPENAI_API_BASE'. If these are not found, it attempts to read from the specified files in the
          'key_file_path' directory.
        - The API version for Azure configurations is set to DEFAULT_AZURE_API_VERSION by default.
        - If 'exclude' is set to 'openai', only Azure OpenAI configurations are returned, and vice versa.
        - The function assumes that the API keys and base URLs in the environment variables are separated by new lines if there are
          multiple entries.
    """
    if exclude != "openai" and key_file_path is not None:
        # skip if key_file_path is None
        if openai_api_key_file is not None:
            # skip if openai_api_key_file is None
            try:
                with open(f"{key_file_path}/{openai_api_key_file}") as key_file:
                    os.environ["OPENAI_API_KEY"] = key_file.read().strip()
            except FileNotFoundError:
                logging.info(
                    "OPENAI_API_KEY is not found in os.environ "
                    "and key_openai.txt is not found in the specified path. You can specify the api_key in the config_list."
                )
        if openai_api_base_file is not None:
            # skip if openai_api_base_file is None
            try:
                with open(f"{key_file_path}/{openai_api_base_file}") as key_file:
                    os.environ["OPENAI_API_BASE"] = key_file.read().strip()
            except FileNotFoundError:
                logging.info(
                    "OPENAI_API_BASE is not found in os.environ "
                    "and base_openai.txt is not found in the specified path. You can specify the base_url in the config_list."
                )
    if exclude != "aoai" and key_file_path is not None:
        # skip if key_file_path is None
        if aoai_api_key_file is not None:
            try:
                with open(f"{key_file_path}/{aoai_api_key_file}") as key_file:
                    os.environ["AZURE_OPENAI_API_KEY"] = key_file.read().strip()
            except FileNotFoundError:
                logging.info(
                    "AZURE_OPENAI_API_KEY is not found in os.environ "
                    "and key_aoai.txt is not found in the specified path. You can specify the api_key in the config_list."
                )
        if aoai_api_base_file is not None:
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
            api_version=DEFAULT_AZURE_API_VERSION,
        )
        if exclude != "aoai"
        else []
    )
    # process openai base urls
    base_urls_env_var = os.environ.get("OPENAI_API_BASE", None)
    base_urls = base_urls_env_var if base_urls_env_var is None else base_urls_env_var.split("\n")
    openai_config = (
        get_config_list(
            # Assuming OpenAI API_KEY in os.environ["OPENAI_API_KEY"]
            api_keys=os.environ.get("OPENAI_API_KEY", "").split("\n"),
            base_urls=base_urls,
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
    model_list: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get a list of configs for API calls with models specified in the model list.

    This function extends `config_list_openai_aoai` by allowing to clone its' out for each of the models provided.
    Each configuration will have a 'model' key with the model name as its value. This is particularly useful when
    all endpoints have same set of models.

    Args:
        key_file_path (str, optional): The path to the key files.
        openai_api_key_file (str, optional): The file name of the OpenAI API key.
        aoai_api_key_file (str, optional): The file name of the Azure OpenAI API key.
        aoai_api_base_file (str, optional): The file name of the Azure OpenAI API base.
        exclude (str, optional): The API type to exclude, "openai" or "aoai".
        model_list (list, optional): The list of model names to include in the configs.

    Returns:
        list: A list of configs for OpenAI API calls, each including model information.

    Example:
    ```python
    # Define the path where the API key files are located
    key_file_path = '/path/to/key/files'

    # Define the file names for the OpenAI and Azure OpenAI API keys and bases
    openai_api_key_file = 'key_openai.txt'
    aoai_api_key_file = 'key_aoai.txt'
    aoai_api_base_file = 'base_aoai.txt'

    # Define the list of models for which to create configurations
    model_list = ['gpt-4', 'gpt-3.5-turbo']

    # Call the function to get a list of configuration dictionaries
    config_list = config_list_from_models(
        key_file_path=key_file_path,
        openai_api_key_file=openai_api_key_file,
        aoai_api_key_file=aoai_api_key_file,
        aoai_api_base_file=aoai_api_base_file,
        model_list=model_list
    )

    # The `config_list` will contain configurations for the specified models, for example:
    # [
    #     {'api_key': '...', 'base_url': 'https://api.openai.com', 'model': 'gpt-4'},
    #     {'api_key': '...', 'base_url': 'https://api.openai.com', 'model': 'gpt-3.5-turbo'}
    # ]
    ```
    """
    config_list = config_list_openai_aoai(
        key_file_path=key_file_path,
        openai_api_key_file=openai_api_key_file,
        aoai_api_key_file=aoai_api_key_file,
        aoai_api_base_file=aoai_api_base_file,
        exclude=exclude,
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
) -> List[Dict[str, Any]]:
    """Get a list of configs for 'gpt-4' followed by 'gpt-3.5-turbo' API calls.

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


def filter_config(
    config_list: List[Dict[str, Any]],
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]], Set[Union[str, None]]]]],
) -> List[Dict[str, Any]]:
    """
    This function filters `config_list` by checking each configuration dictionary against the
    criteria specified in `filter_dict`. A configuration dictionary is retained if for every
    key in `filter_dict`, see example below.

    Args:
        config_list (list of dict): A list of configuration dictionaries to be filtered.
        filter_dict (dict): A dictionary representing the filter criteria, where each key is a
                            field name to check within the configuration dictionaries, and the
                            corresponding value is a list of acceptable values for that field.
                            If the configuration's field's value is not a list, then a match occurs
                            when it is found in the list of acceptable values. If the configuration's
                            field's value is a list, then a match occurs if there is a non-empty
                            intersection with the acceptable values.


    Returns:
        list of dict: A list of configuration dictionaries that meet all the criteria specified
                      in `filter_dict`.

    Example:
    ```python
    # Example configuration list with various models and API types
    configs = [
        {'model': 'gpt-3.5-turbo'},
        {'model': 'gpt-4'},
        {'model': 'gpt-3.5-turbo', 'api_type': 'azure'},
        {'model': 'gpt-3.5-turbo', 'tags': ['gpt35_turbo', 'gpt-35-turbo']},
    ]

    # Define filter criteria to select configurations for the 'gpt-3.5-turbo' model
    # that are also using the 'azure' API type
    filter_criteria = {
        'model': ['gpt-3.5-turbo'],  # Only accept configurations for 'gpt-3.5-turbo'
        'api_type': ['azure']       # Only accept configurations for 'azure' API type
    }

    # Apply the filter to the configuration list
    filtered_configs = filter_config(configs, filter_criteria)

    # The resulting `filtered_configs` will be:
    # [{'model': 'gpt-3.5-turbo', 'api_type': 'azure', ...}]


    # Define a filter to select a given tag
    filter_criteria = {
        'tags': ['gpt35_turbo'],
    }

    # Apply the filter to the configuration list
    filtered_configs = filter_config(configs, filter_criteria)

    # The resulting `filtered_configs` will be:
    # [{'model': 'gpt-3.5-turbo', 'tags': ['gpt35_turbo', 'gpt-35-turbo']}]
    ```

    Note:
        - If `filter_dict` is empty or None, no filtering is applied and `config_list` is returned as is.
        - If a configuration dictionary in `config_list` does not contain a key specified in `filter_dict`,
          it is considered a non-match and is excluded from the result.
        - If the list of acceptable values for a key in `filter_dict` includes None, then configuration
          dictionaries that do not have that key will also be considered a match.
    """

    def _satisfies(config_value: Any, acceptable_values: Any) -> bool:
        if isinstance(config_value, list):
            return bool(set(config_value) & set(acceptable_values))  # Non-empty intersection
        else:
            return config_value in acceptable_values

    if filter_dict:
        config_list = [
            config
            for config in config_list
            if all(_satisfies(config.get(key), value) for key, value in filter_dict.items())
        ]
    return config_list


def config_list_from_json(
    env_or_file: str,
    file_location: Optional[str] = "",
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]], Set[Union[str, None]]]]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves a list of API configurations from a JSON stored in an environment variable or a file.

    This function attempts to parse JSON data from the given `env_or_file` parameter. If `env_or_file` is an
    environment variable containing JSON data, it will be used directly. Otherwise, it is assumed to be a filename,
    and the function will attempt to read the file from the specified `file_location`.

    The `filter_dict` parameter allows for filtering the configurations based on specified criteria. Each key in the
    `filter_dict` corresponds to a field in the configuration dictionaries, and the associated value is a list or set
    of acceptable values for that field. If a field is missing in a configuration and `None` is included in the list
    of acceptable values for that field, the configuration will still be considered a match.

    Args:
        env_or_file (str): The name of the environment variable, the filename, or the environment variable of the filename
            that containing the JSON data.
        file_location (str, optional): The directory path where the file is located, if `env_or_file` is a filename.
        filter_dict (dict, optional): A dictionary specifying the filtering criteria for the configurations, with
            keys representing field names and values being lists or sets of acceptable values for those fields.

    Example:
    ```python
    # Suppose we have an environment variable 'CONFIG_JSON' with the following content:
    # '[{"model": "gpt-3.5-turbo", "api_type": "azure"}, {"model": "gpt-4"}]'

    # We can retrieve a filtered list of configurations like this:
    filter_criteria = {"model": ["gpt-3.5-turbo"]}
    configs = config_list_from_json('CONFIG_JSON', filter_dict=filter_criteria)
    # The 'configs' variable will now contain only the configurations that match the filter criteria.
    ```

    Returns:
        List[Dict]: A list of configuration dictionaries that match the filtering criteria specified in `filter_dict`.

    Raises:
        FileNotFoundError: if env_or_file is neither found as an environment variable nor a file
    """
    env_str = os.environ.get(env_or_file)

    if env_str:
        # The environment variable exists. We should use information from it.
        if os.path.exists(env_str):
            # It is a file location, and we need to load the json from the file.
            with open(env_str, "r") as file:
                json_str = file.read()
        else:
            # Else, it should be a JSON string by itself.
            json_str = env_str
        config_list = json.loads(json_str)
    else:
        # The environment variable does not exist.
        # So, `env_or_file` is a filename. We should use the file location.
        if file_location is not None:
            config_list_path = os.path.join(file_location, env_or_file)
        else:
            config_list_path = env_or_file

        with open(config_list_path) as json_file:
            config_list = json.load(json_file)
    return filter_config(config_list, filter_dict)


def get_config(
    api_key: Optional[str],
    base_url: Optional[str] = None,
    api_type: Optional[str] = None,
    api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs a configuration dictionary for a single model with the provided API configurations.

    Example:
    ```python
    config = get_config(
        api_key="sk-abcdef1234567890",
        base_url="https://api.openai.com",
        api_version="v1"
    )
    # The 'config' variable will now contain:
    # {
    #     "api_key": "sk-abcdef1234567890",
    #     "base_url": "https://api.openai.com",
    #     "api_version": "v1"
    # }
    ```

    Args:
        api_key (str): The API key for authenticating API requests.
        base_url (Optional[str]): The base URL of the API. If not provided, defaults to None.
        api_type (Optional[str]): The type of API. If not provided, defaults to None.
        api_version (Optional[str]): The version of the API. If not provided, defaults to None.

    Returns:
        Dict: A dictionary containing the provided API configurations.
    """
    config = {"api_key": api_key}
    if base_url:
        config["base_url"] = os.getenv(base_url, default=base_url)
    if api_type:
        config["api_type"] = os.getenv(api_type, default=api_type)
    if api_version:
        config["api_version"] = os.getenv(api_version, default=api_version)
    return config


def config_list_from_dotenv(
    dotenv_file_path: Optional[str] = None,
    model_api_key_map: Optional[Dict[str, Any]] = None,
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]], Set[Union[str, None]]]]] = None,
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
        dotenv_path_str = find_dotenv()
        if not dotenv_path_str:
            logging.warning("No .env file found. Loading configurations from environment variables.")
        dotenv_path = Path(dotenv_path_str)
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


def retrieve_assistants_by_name(client: OpenAI, name: str) -> List[Assistant]:
    """
    Return the assistants with the given name from OAI assistant API
    """
    assistants = client.beta.assistants.list()
    candidate_assistants = []
    for assistant in assistants.data:
        if assistant.name == name:
            candidate_assistants.append(assistant)
    return candidate_assistants
