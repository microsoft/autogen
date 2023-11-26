from __future__ import annotations

import os
import sys
from typing import List, Optional, Dict, Callable
import logging
import inspect
from flaml.automl.logger import logger_formatter

from autogen.oai.openai_utils import get_key
from autogen.token_count_utils import count_token

try:
    from openai import OpenAI, APIError
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
    from openai.types.completion import Completion
    from openai.types.completion_usage import CompletionUsage
    import diskcache

    ERROR = None
except ImportError:
    ERROR = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")
    OpenAI = object
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)


class OpenAIWrapper:
    """A wrapper class for openai client."""

    cache_path_root: str = ".cache"
    extra_kwargs = {"cache_seed", "filter_func", "allow_format_str_template", "context", "api_version"}
    openai_kwargs = set(inspect.getfullargspec(OpenAI.__init__).kwonlyargs)

    def __init__(self, *, config_list: List[Dict] = None, **base_config):
        """
        Args:
            config_list: a list of config dicts to override the base_config.
                They can contain additional kwargs as allowed in the [create](/docs/reference/oai/client#create) method. E.g.,

        ```python
        config_list=[
            {
                "model": "gpt-4",
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_type": "azure",
                "base_url": os.environ.get("AZURE_OPENAI_API_BASE"),
                "api_version": "2023-03-15-preview",
            },
            {
                "model": "gpt-3.5-turbo",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "api_type": "open_ai",
                "base_url": "https://api.openai.com/v1",
            },
            {
                "model": "llama-7B",
                "base_url": "http://127.0.0.1:8080",
                "api_type": "open_ai",
            }
        ]
        ```

            base_config: base config. It can contain both keyword arguments for openai client
                and additional kwargs.
        """
        openai_config, extra_kwargs = self._separate_openai_config(base_config)
        if type(config_list) is list and len(config_list) == 0:
            logger.warning("openai client was provided with an empty config_list, which may not be intended.")
        if config_list:
            config_list = [config.copy() for config in config_list]  # make a copy before modifying
            self._clients = [self._client(config, openai_config) for config in config_list]  # could modify the config
            self._config_list = [
                {**extra_kwargs, **{k: v for k, v in config.items() if k not in self.openai_kwargs}}
                for config in config_list
            ]
        else:
            self._clients = [self._client(extra_kwargs, openai_config)]
            self._config_list = [extra_kwargs]

    def _process_for_azure(self, config: Dict, extra_kwargs: Dict, segment: str = "default"):
        # deal with api_version
        query_segment = f"{segment}_query"
        headers_segment = f"{segment}_headers"
        api_version = extra_kwargs.get("api_version")
        if api_version is not None and query_segment not in config:
            config[query_segment] = {"api-version": api_version}
            if segment == "default":
                # remove the api_version from extra_kwargs
                extra_kwargs.pop("api_version")
        if segment == "extra":
            return
        # deal with api_type
        api_type = extra_kwargs.get("api_type")
        if api_type is not None and api_type.startswith("azure") and headers_segment not in config:
            api_key = config.get("api_key", os.environ.get("AZURE_OPENAI_API_KEY"))
            config[headers_segment] = {"api-key": api_key}
            # remove the api_type from extra_kwargs
            extra_kwargs.pop("api_type")
            # deal with model
            model = extra_kwargs.get("model")
            if model is None:
                return
            if "gpt-3.5" in model:
                # hack for azure gpt-3.5
                extra_kwargs["model"] = model = model.replace("gpt-3.5", "gpt-35")
            base_url = config.get("base_url")
            if base_url is None:
                raise ValueError("to use azure openai api, base_url must be specified.")
            suffix = f"/openai/deployments/{model}"
            if not base_url.endswith(suffix):
                config["base_url"] += suffix[1:] if base_url.endswith("/") else suffix

    def _separate_openai_config(self, config):
        """Separate the config into openai_config and extra_kwargs."""
        openai_config = {k: v for k, v in config.items() if k in self.openai_kwargs}
        extra_kwargs = {k: v for k, v in config.items() if k not in self.openai_kwargs}
        self._process_for_azure(openai_config, extra_kwargs)
        return openai_config, extra_kwargs

    def _separate_create_config(self, config):
        """Separate the config into create_config and extra_kwargs."""
        create_config = {k: v for k, v in config.items() if k not in self.extra_kwargs}
        extra_kwargs = {k: v for k, v in config.items() if k in self.extra_kwargs}
        return create_config, extra_kwargs

    def _client(self, config, openai_config):
        """Create a client with the given config to overrdie openai_config,
        after removing extra kwargs.
        """
        openai_config = {**openai_config, **{k: v for k, v in config.items() if k in self.openai_kwargs}}
        self._process_for_azure(openai_config, config)
        client = OpenAI(**openai_config)
        return client

    @classmethod
    def instantiate(
        cls,
        template: str | Callable | None,
        context: Optional[Dict] = None,
        allow_format_str_template: Optional[bool] = False,
    ):
        if not context or template is None:
            return template
        if isinstance(template, str):
            return template.format(**context) if allow_format_str_template else template
        return template(context)

    def _construct_create_params(self, create_config: Dict, extra_kwargs: Dict) -> Dict:
        """Prime the create_config with additional_kwargs."""
        # Validate the config
        prompt = create_config.get("prompt")
        messages = create_config.get("messages")
        if (prompt is None) == (messages is None):
            raise ValueError("Either prompt or messages should be in create config but not both.")
        context = extra_kwargs.get("context")
        if context is None:
            # No need to instantiate if no context is provided.
            return create_config
        # Instantiate the prompt or messages
        allow_format_str_template = extra_kwargs.get("allow_format_str_template", False)
        # Make a copy of the config
        params = create_config.copy()
        if prompt is not None:
            # Instantiate the prompt
            params["prompt"] = self.instantiate(prompt, context, allow_format_str_template)
        elif context:
            # Instantiate the messages
            params["messages"] = [
                {
                    **m,
                    "content": self.instantiate(m["content"], context, allow_format_str_template),
                }
                if m.get("content")
                else m
                for m in messages
            ]
        return params

    def create(self, **config):
        """Make a completion for a given config using openai's clients.
        Besides the kwargs allowed in openai's client, we allow the following additional kwargs.
        The config in each client will be overriden by the config.

        Args:
            - context (Dict | None): The context to instantiate the prompt or messages. Default to None.
                It needs to contain keys that are used by the prompt template or the filter function.
                E.g., `prompt="Complete the following sentence: {prefix}, context={"prefix": "Today I feel"}`.
                The actual prompt will be:
                "Complete the following sentence: Today I feel".
                More examples can be found at [templating](/docs/Use-Cases/enhanced_inference#templating).
            - `cache_seed` (int | None) for the cache. Default to 41.
                An integer cache_seed is useful when implementing "controlled randomness" for the completion.
                None for no caching.
            - filter_func (Callable | None): A function that takes in the context and the response
                and returns a boolean to indicate whether the response is valid. E.g.,

        ```python
        def yes_or_no_filter(context, response):
            return context.get("yes_or_no_choice", False) is False or any(
                text in ["Yes.", "No."] for text in client.extract_text_or_function_call(response)
            )
        ```

            - allow_format_str_template (bool | None): Whether to allow format string template in the config. Default to false.
            - api_version (str | None): The api version. Default to None. E.g., "2023-08-01-preview".
        """
        if ERROR:
            raise ERROR
        last = len(self._clients) - 1
        for i, client in enumerate(self._clients):
            # merge the input config with the i-th config in the config list
            full_config = {**config, **self._config_list[i]}
            # separate the config into create_config and extra_kwargs
            create_config, extra_kwargs = self._separate_create_config(full_config)
            # process for azure
            self._process_for_azure(create_config, extra_kwargs, "extra")
            # construct the create params
            params = self._construct_create_params(create_config, extra_kwargs)
            # get the cache_seed, filter_func and context
            cache_seed = extra_kwargs.get("cache_seed", 41)
            filter_func = extra_kwargs.get("filter_func")
            context = extra_kwargs.get("context")

            # Try to load the response from cache
            if cache_seed is not None:
                with diskcache.Cache(f"{self.cache_path_root}/{cache_seed}") as cache:
                    # Try to get the response from cache
                    key = get_key(params)
                    response = cache.get(key, None)
                    if response is not None:
                        # check the filter
                        pass_filter = filter_func is None or filter_func(context=context, response=response)
                        if pass_filter or i == last:
                            # Return the response if it passes the filter or it is the last client
                            response.config_id = i
                            response.pass_filter = pass_filter
                            # TODO: add response.cost
                            return response
                        continue  # filter is not passed; try the next config
            try:
                response = self._completions_create(client, params)
            except APIError:
                logger.debug(f"config {i} failed", exc_info=1)
                if i == last:
                    raise
            else:
                if cache_seed is not None:
                    # Cache the response
                    with diskcache.Cache(f"{self.cache_path_root}/{cache_seed}") as cache:
                        cache.set(key, response)

                # check the filter
                pass_filter = filter_func is None or filter_func(context=context, response=response)
                if pass_filter or i == last:
                    # Return the response if it passes the filter or it is the last client
                    response.config_id = i
                    response.pass_filter = pass_filter
                    # TODO: add response.cost
                    return response
                continue  # filter is not passed; try the next config

    def _completions_create(self, client, params):
        completions = client.chat.completions if "messages" in params else client.completions
        # If streaming is enabled, has messages, and does not have functions, then
        # iterate over the chunks of the response
        if params.get("stream", False) and "messages" in params and "functions" not in params:
            response_contents = [""] * params.get("n", 1)
            finish_reasons = [""] * params.get("n", 1)
            completion_tokens = 0

            # Set the terminal text color to green
            print("\033[32m", end="")

            # Send the chat completion request to OpenAI's API and process the response in chunks
            for chunk in completions.create(**params):
                if chunk.choices:
                    for choice in chunk.choices:
                        content = choice.delta.content
                        finish_reasons[choice.index] = choice.finish_reason
                        # If content is present, print it to the terminal and update response variables
                        if content is not None:
                            print(content, end="", flush=True)
                            response_contents[choice.index] += content
                            completion_tokens += 1
                        else:
                            print()

            # Reset the terminal text color
            print("\033[0m\n")

            # Prepare the final ChatCompletion object based on the accumulated data
            model = chunk.model.replace("gpt-35", "gpt-3.5")  # hack for Azure API
            prompt_tokens = count_token(params["messages"], model)
            response = ChatCompletion(
                id=chunk.id,
                model=chunk.model,
                created=chunk.created,
                object="chat.completion",
                choices=[],
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
            for i in range(len(response_contents)):
                response.choices.append(
                    Choice(
                        index=i,
                        finish_reason=finish_reasons[i],
                        message=ChatCompletionMessage(
                            role="assistant", content=response_contents[i], function_call=None
                        ),
                    )
                )
        else:
            # If streaming is not enabled or using functions, send a regular chat completion request
            # Functions are not supported, so ensure streaming is disabled
            params = params.copy()
            params["stream"] = False
            response = completions.create(**params)
        return response

    @classmethod
    def extract_text_or_function_call(cls, response: ChatCompletion | Completion) -> List[str]:
        """Extract the text or function calls from a completion or chat response.

        Args:
            response (ChatCompletion | Completion): The response from openai.

        Returns:
            A list of text or function calls in the responses.
        """
        choices = response.choices
        if isinstance(response, Completion):
            return [choice.text for choice in choices]
        return [
            choice.message if choice.message.function_call is not None else choice.message.content for choice in choices
        ]


# TODO: logging
