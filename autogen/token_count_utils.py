from typing import List, Union, Dict
import logging
import json
import tiktoken
import re
from transformers import AutoTokenizer
from .oai.openai_utils import config_list_from_json

logger = logging.getLogger(__name__)


def get_max_token_limit(model: str = "gpt-3.5-turbo-0613") -> int:
    # Handle common azure model names/aliases
    model = re.sub(r"^gpt\-?35", "gpt-3.5", model)
    model = re.sub(r"^gpt4", "gpt-4", model)

    max_token_limit = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-0301": 4096,
        "gpt-3.5-turbo-0613": 4096,
        "gpt-3.5-turbo-instruct": 4096,
        "gpt-3.5-turbo-16k": 16385,
        "gpt-3.5-turbo-16k-0613": 16385,
        "gpt-3.5-turbo-1106": 16385,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-32k-0314": 32768,  # deprecate in Sep
        "gpt-4-0314": 8192,  # deprecate in Sep
        "gpt-4-0613": 8192,
        "gpt-4-32k-0613": 32768,
        "gpt-4-1106-preview": 128000,
        "gpt-4-0125-preview": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-4-vision-preview": 128000,
    }
    return max_token_limit[model]


def percentile_used(input, model="gpt-3.5-turbo-0613"):
    return count_token(input) / get_max_token_limit(model)


def token_left(input: Union[str, List, Dict], model="gpt-3.5-turbo-0613") -> int:
    """Count number of tokens left for an OpenAI model.

    Args:
        input: (str, list, dict): Input to the model.
        model: (str): Model name.

    Returns:
        int: Number of tokens left that the model can use for completion.
    """
    return get_max_token_limit(model) - count_token(input, model=model)


def count_token(input: Union[str, List, Dict], model: str = "gpt-3.5-turbo-0613") -> int:
    """Count number of tokens used by an OpenAI model.
    Args:
        input: (str, list, dict): Input to the model.
        model: (str): Model name.

    Returns:
        int: Number of tokens from the input.
    """
    if isinstance(input, str):
        return _num_token_from_text(input, model=model)
    elif isinstance(input, list) or isinstance(input, dict):
        return _num_token_from_messages(input, model=model)
    else:
        raise ValueError("input must be str, list or dict")

def _num_token_from_text(text: str, model: str = "gpt-3.5-turbo-0613", oai_config_file = "OAI_CONFIG_LIST"):
    """Return the number of tokens used by a string.
    If you are using an open source llm you can specify a custom tokenizer and its kwargs in your OAI_CONFIG_LIST.
    """

    def use_cl100k_base_encoding():
        logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    def use_autotokenizer(model_path_for_tokenizer: str, tokenizer_kwargs: dict):
        logger.warning(f"Using AutoTokenizer with model_path:{model_path_for_tokenizer} for model:{model}.")
        tokenizer = AutoTokenizer.from_pretrained(model_path_for_tokenizer, **tokenizer_kwargs)
        return len(tokenizer(text, return_tensors="pt").input_ids[0])

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))

    except KeyError:
        try:
            config_list = config_list_from_json(
                oai_config_file,
                filter_dict={"model": [model]},
            )

            if len(config_list) != 1 or config_list[0].get('model_path_for_tokenizer') is None:
                return use_cl100k_base_encoding()

            model_path_for_tokenizer = config_list[0]['model_path_for_tokenizer']

            # Extract additional parameters for tokenizer from the config
            tokenizer_kwargs = config_list[0].get('tokenizer_kwargs', {})

            return use_autotokenizer(model_path_for_tokenizer, tokenizer_kwargs)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}. Model path for tokenizer not found for model: {model}.")
            return use_cl100k_base_encoding()

def _num_token_from_messages(messages: Union[List, Dict], model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages.

    retrieved from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb/
    """
    if isinstance(messages, dict):
        messages = [messages]

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        logger.info("gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return _num_token_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        logger.info("gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return _num_token_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""_num_token_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if value is None:
                continue

            # function calls
            if not isinstance(value, str):
                try:
                    value = json.dumps(value)
                except TypeError:
                    logger.warning(
                        f"Value {value} is not a string and cannot be converted to json. It is a type: {type(value)} Skipping."
                    )
                    continue

            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def num_tokens_from_functions(functions, model="gpt-3.5-turbo-0613") -> int:
    """Return the number of tokens used by a list of functions.

    Args:
        functions: (list): List of function descriptions that will be passed in model.
        model: (str): Model name.

    Returns:
        int: Number of tokens from the function descriptions.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for function in functions:
        function_tokens = len(encoding.encode(function["name"]))
        function_tokens += len(encoding.encode(function["description"]))
        function_tokens -= 2
        if "parameters" in function:
            parameters = function["parameters"]
            if "properties" in parameters:
                for propertiesKey in parameters["properties"]:
                    function_tokens += len(encoding.encode(propertiesKey))
                    v = parameters["properties"][propertiesKey]
                    for field in v:
                        if field == "type":
                            function_tokens += 2
                            function_tokens += len(encoding.encode(v["type"]))
                        elif field == "description":
                            function_tokens += 2
                            function_tokens += len(encoding.encode(v["description"]))
                        elif field == "enum":
                            function_tokens -= 3
                            for o in v["enum"]:
                                function_tokens += 3
                                function_tokens += len(encoding.encode(o))
                        else:
                            print(f"Warning: not supported field {field}")
                function_tokens += 11
                if len(parameters["properties"]) == 0:
                    function_tokens -= 2

        num_tokens += function_tokens

    num_tokens += 12
    return num_tokens
