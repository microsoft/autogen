from __future__ import annotations

import os
import sys
from typing import Any, List, Optional, Dict, Callable, Tuple, Union
import logging
import inspect
from flaml.automl.logger import logger_formatter

from pydantic import BaseModel

from autogen.cache.cache import Cache
from autogen.oai import completion

from autogen.oai.openai_utils import DEFAULT_AZURE_API_VERSION, get_key, OAI_PRICE1K
from autogen.token_count_utils import count_token
from autogen._pydantic import model_dump

TOOL_ENABLED = False
try:
    import openai
except ImportError:
    ERROR: Optional[ImportError] = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")
    OpenAI = object
    AzureOpenAI = object
else:
    # raises exception if openai>=1 is installed and something is wrong with imports
    from openai import OpenAI, AzureOpenAI, APIError, __version__ as OPENAIVERSION
    from openai.resources import Completions
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice  # type: ignore [attr-defined]
    from openai.types.chat.chat_completion_chunk import (
        ChoiceDeltaToolCall,
        ChoiceDeltaToolCallFunction,
        ChoiceDeltaFunctionCall,
    )
    from openai.types.completion import Completion
    from openai.types.completion_usage import CompletionUsage

    if openai.__version__ >= "1.1.0":
        TOOL_ENABLED = True
    ERROR = None

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)

LEGACY_DEFAULT_CACHE_SEED = 41
LEGACY_CACHE_DIR = ".cache"


class OpenAIWrapper:
    """A wrapper class for openai client."""

    extra_kwargs = {
        "cache",
        "cache_seed",
        "filter_func",
        "allow_format_str_template",
        "context",
        "api_version",
        "api_type",
        "tags",
    }

    openai_kwargs = set(inspect.getfullargspec(OpenAI.__init__).kwonlyargs)
    aopenai_kwargs = set(inspect.getfullargspec(AzureOpenAI.__init__).kwonlyargs)
    openai_kwargs = openai_kwargs | aopenai_kwargs
    total_usage_summary: Optional[Dict[str, Any]] = None
    actual_usage_summary: Optional[Dict[str, Any]] = None

    def __init__(self, *, config_list: Optional[List[Dict[str, Any]]] = None, **base_config: Any):
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
            self._clients: List[OpenAI] = [
                self._client(config, openai_config) for config in config_list
            ]  # could modify the config
            self._config_list = [
                {**extra_kwargs, **{k: v for k, v in config.items() if k not in self.openai_kwargs}}
                for config in config_list
            ]
        else:
            self._clients = [self._client(extra_kwargs, openai_config)]
            self._config_list = [extra_kwargs]

    def _separate_openai_config(self, config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Separate the config into openai_config and extra_kwargs."""
        openai_config = {k: v for k, v in config.items() if k in self.openai_kwargs}
        extra_kwargs = {k: v for k, v in config.items() if k not in self.openai_kwargs}
        return openai_config, extra_kwargs

    def _separate_create_config(self, config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Separate the config into create_config and extra_kwargs."""
        create_config = {k: v for k, v in config.items() if k not in self.extra_kwargs}
        extra_kwargs = {k: v for k, v in config.items() if k in self.extra_kwargs}
        return create_config, extra_kwargs

    def _client(self, config: Dict[str, Any], openai_config: Dict[str, Any]) -> OpenAI:
        """Create a client with the given config to override openai_config,
        after removing extra kwargs.

        For Azure models/deployment names there's a convenience modification of model removing dots in
        the it's value (Azure deploment names can't have dots). I.e. if you have Azure deployment name
        "gpt-35-turbo" and define model "gpt-3.5-turbo" in the config the function will remove the dot
        from the name and create a client that connects to "gpt-35-turbo" Azure deployment.
        """
        openai_config = {**openai_config, **{k: v for k, v in config.items() if k in self.openai_kwargs}}
        api_type = config.get("api_type")
        if api_type is not None and api_type.startswith("azure"):
            openai_config["azure_deployment"] = openai_config.get("azure_deployment", config.get("model"))
            if openai_config["azure_deployment"] is not None:
                openai_config["azure_deployment"] = openai_config["azure_deployment"].replace(".", "")
            openai_config["azure_endpoint"] = openai_config.get("azure_endpoint", openai_config.pop("base_url", None))
            client = AzureOpenAI(**openai_config)
        else:
            client = OpenAI(**openai_config)
        return client

    @classmethod
    def instantiate(
        cls,
        template: Optional[Union[str, Callable[[Dict[str, Any]], str]]],
        context: Optional[Dict[str, Any]] = None,
        allow_format_str_template: Optional[bool] = False,
    ) -> Optional[str]:
        if not context or template is None:
            return template  # type: ignore [return-value]
        if isinstance(template, str):
            return template.format(**context) if allow_format_str_template else template
        return template(context)

    def _construct_create_params(self, create_config: Dict[str, Any], extra_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Prime the create_config with additional_kwargs."""
        # Validate the config
        prompt: Optional[str] = create_config.get("prompt")
        messages: Optional[List[Dict[str, Any]]] = create_config.get("messages")
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
                for m in messages  # type: ignore [union-attr]
            ]
        return params

    def create(self, **config: Any) -> ChatCompletion:
        """Make a completion for a given config using openai's clients.
        Besides the kwargs allowed in openai's client, we allow the following additional kwargs.
        The config in each client will be overridden by the config.

        Args:
            - context (Dict | None): The context to instantiate the prompt or messages. Default to None.
                It needs to contain keys that are used by the prompt template or the filter function.
                E.g., `prompt="Complete the following sentence: {prefix}, context={"prefix": "Today I feel"}`.
                The actual prompt will be:
                "Complete the following sentence: Today I feel".
                More examples can be found at [templating](/docs/Use-Cases/enhanced_inference#templating).
            - cache (Cache | None): A Cache object to use for response cache. Default to None.
                Note that the cache argument overrides the legacy cache_seed argument: if this argument is provided,
                then the cache_seed argument is ignored. If this argument is not provided or None,
                then the cache_seed argument is used.
            - (Legacy) cache_seed (int | None) for using the DiskCache. Default to 41.
                An integer cache_seed is useful when implementing "controlled randomness" for the completion.
                None for no caching.
                Note: this is a legacy argument. It is only used when the cache argument is not provided.
            - filter_func (Callable | None): A function that takes in the context and the response
                and returns a boolean to indicate whether the response is valid. E.g.,

        ```python
        def yes_or_no_filter(context, response):
            return context.get("yes_or_no_choice", False) is False or any(
                text in ["Yes.", "No."] for text in client.extract_text_or_completion_object(response)
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
            api_type = extra_kwargs.get("api_type")
            if api_type and api_type.startswith("azure") and "model" in create_config:
                create_config["model"] = create_config["model"].replace(".", "")
            # construct the create params
            params = self._construct_create_params(create_config, extra_kwargs)
            # get the cache_seed, filter_func and context
            cache_seed = extra_kwargs.get("cache_seed", LEGACY_DEFAULT_CACHE_SEED)
            cache = extra_kwargs.get("cache")
            filter_func = extra_kwargs.get("filter_func")
            context = extra_kwargs.get("context")

            cache_client = None
            if cache is not None:
                # Use the cache object if provided.
                cache_client = cache
            elif cache_seed is not None:
                # Legacy cache behavior, if cache_seed is given, use DiskCache.
                cache_client = Cache.disk(cache_seed, LEGACY_CACHE_DIR)

            if cache_client is not None:
                with cache_client as cache:
                    # Try to get the response from cache
                    key = get_key(params)
                    response: ChatCompletion = cache.get(key, None)

                    if response is not None:
                        try:
                            response.cost  # type: ignore [attr-defined]
                        except AttributeError:
                            # update attribute if cost is not calculated
                            response.cost = self.cost(response)
                            cache.set(key, response)
                        self._update_usage_summary(response, use_cache=True)
                        # check the filter
                        pass_filter = filter_func is None or filter_func(context=context, response=response)
                        if pass_filter or i == last:
                            # Return the response if it passes the filter or it is the last client
                            response.config_id = i
                            response.pass_filter = pass_filter
                            return response
                        continue  # filter is not passed; try the next config
            try:
                response = self._completions_create(client, params)
            except APIError as err:
                error_code = getattr(err, "code", None)
                if error_code == "content_filter":
                    # raise the error for content_filter
                    raise
                logger.debug(f"config {i} failed", exc_info=True)
                if i == last:
                    raise
            else:
                # add cost calculation before caching no matter filter is passed or not
                response.cost = self.cost(response)
                self._update_usage_summary(response, use_cache=False)
                if cache_client is not None:
                    # Cache the response
                    with cache_client as cache:
                        cache.set(key, response)

                # check the filter
                pass_filter = filter_func is None or filter_func(context=context, response=response)
                if pass_filter or i == last:
                    # Return the response if it passes the filter or it is the last client
                    response.config_id = i
                    response.pass_filter = pass_filter
                    return response
                continue  # filter is not passed; try the next config
        raise RuntimeError("Should not reach here.")

    @staticmethod
    def _update_dict_from_chunk(chunk: BaseModel, d: Dict[str, Any], field: str) -> int:
        """Update the dict from the chunk.

        Reads `chunk.field` and if present updates `d[field]` accordingly.

        Args:
            chunk: The chunk.
            d: The dict to be updated in place.
            field: The field.

        Returns:
            The updated dict.

        """
        completion_tokens = 0
        assert isinstance(d, dict), d
        if hasattr(chunk, field) and getattr(chunk, field) is not None:
            new_value = getattr(chunk, field)
            if isinstance(new_value, list) or isinstance(new_value, dict):
                raise NotImplementedError(
                    f"Field {field} is a list or dict, which is currently not supported. "
                    "Only string and numbers are supported."
                )
            if field not in d:
                d[field] = ""
            if isinstance(new_value, str):
                d[field] += getattr(chunk, field)
            else:
                d[field] = new_value
            completion_tokens = 1

        return completion_tokens

    @staticmethod
    def _update_function_call_from_chunk(
        function_call_chunk: Union[ChoiceDeltaToolCallFunction, ChoiceDeltaFunctionCall],
        full_function_call: Optional[Dict[str, Any]],
        completion_tokens: int,
    ) -> Tuple[Dict[str, Any], int]:
        """Update the function call from the chunk.

        Args:
            function_call_chunk: The function call chunk.
            full_function_call: The full function call.
            completion_tokens: The number of completion tokens.

        Returns:
            The updated full function call and the updated number of completion tokens.

        """
        # Handle function call
        if function_call_chunk:
            if full_function_call is None:
                full_function_call = {}
            for field in ["name", "arguments"]:
                completion_tokens += OpenAIWrapper._update_dict_from_chunk(
                    function_call_chunk, full_function_call, field
                )

        if full_function_call:
            return full_function_call, completion_tokens
        else:
            raise RuntimeError("Function call is not found, this should not happen.")

    @staticmethod
    def _update_tool_calls_from_chunk(
        tool_calls_chunk: ChoiceDeltaToolCall,
        full_tool_call: Optional[Dict[str, Any]],
        completion_tokens: int,
    ) -> Tuple[Dict[str, Any], int]:
        """Update the tool call from the chunk.

        Args:
            tool_call_chunk: The tool call chunk.
            full_tool_call: The full tool call.
            completion_tokens: The number of completion tokens.

        Returns:
            The updated full tool call and the updated number of completion tokens.

        """
        # future proofing for when tool calls other than function calls are supported
        if tool_calls_chunk.type and tool_calls_chunk.type != "function":
            raise NotImplementedError(
                f"Tool call type {tool_calls_chunk.type} is currently not supported. "
                "Only function calls are supported."
            )

        # Handle tool call
        assert full_tool_call is None or isinstance(full_tool_call, dict), full_tool_call
        if tool_calls_chunk:
            if full_tool_call is None:
                full_tool_call = {}
            for field in ["index", "id", "type"]:
                completion_tokens += OpenAIWrapper._update_dict_from_chunk(tool_calls_chunk, full_tool_call, field)

            if hasattr(tool_calls_chunk, "function") and tool_calls_chunk.function:
                if "function" not in full_tool_call:
                    full_tool_call["function"] = None

                full_tool_call["function"], completion_tokens = OpenAIWrapper._update_function_call_from_chunk(
                    tool_calls_chunk.function, full_tool_call["function"], completion_tokens
                )

        if full_tool_call:
            return full_tool_call, completion_tokens
        else:
            raise RuntimeError("Tool call is not found, this should not happen.")

    def _completions_create(self, client: OpenAI, params: Dict[str, Any]) -> ChatCompletion:
        """Create a completion for a given config using openai's client.

        Args:
            client: The openai client.
            params: The params for the completion.

        Returns:
            The completion.
        """
        completions: Completions = client.chat.completions if "messages" in params else client.completions  # type: ignore [attr-defined]
        # If streaming is enabled and has messages, then iterate over the chunks of the response.
        if params.get("stream", False) and "messages" in params:
            response_contents = [""] * params.get("n", 1)
            finish_reasons = [""] * params.get("n", 1)
            completion_tokens = 0

            # Set the terminal text color to green
            print("\033[32m", end="")

            # Prepare for potential function call
            full_function_call: Optional[Dict[str, Any]] = None
            full_tool_calls: Optional[List[Optional[Dict[str, Any]]]] = None

            # Send the chat completion request to OpenAI's API and process the response in chunks
            for chunk in completions.create(**params):
                if chunk.choices:
                    for choice in chunk.choices:
                        content = choice.delta.content
                        tool_calls_chunks = choice.delta.tool_calls
                        finish_reasons[choice.index] = choice.finish_reason

                        # todo: remove this after function calls are removed from the API
                        # the code should work regardless of whether function calls are removed or not, but test_chat_functions_stream should fail
                        # begin block
                        function_call_chunk = (
                            choice.delta.function_call if hasattr(choice.delta, "function_call") else None
                        )
                        # Handle function call
                        if function_call_chunk:
                            # Handle function call
                            if function_call_chunk:
                                full_function_call, completion_tokens = self._update_function_call_from_chunk(
                                    function_call_chunk, full_function_call, completion_tokens
                                )
                            if not content:
                                continue
                        # end block

                        # Handle tool calls
                        if tool_calls_chunks:
                            for tool_calls_chunk in tool_calls_chunks:
                                # the current tool call to be reconstructed
                                ix = tool_calls_chunk.index
                                if full_tool_calls is None:
                                    full_tool_calls = []
                                if ix >= len(full_tool_calls):
                                    # in case ix is not sequential
                                    full_tool_calls = full_tool_calls + [None] * (ix - len(full_tool_calls) + 1)

                                full_tool_calls[ix], completion_tokens = self._update_tool_calls_from_chunk(
                                    tool_calls_chunk, full_tool_calls[ix], completion_tokens
                                )
                                if not content:
                                    continue

                        # End handle tool calls

                        # If content is present, print it to the terminal and update response variables
                        if content is not None:
                            print(content, end="", flush=True)
                            response_contents[choice.index] += content
                            completion_tokens += 1
                        else:
                            # print()
                            pass

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
                if OPENAIVERSION >= "1.5":  # pragma: no cover
                    # OpenAI versions 1.5.0 and above
                    choice = Choice(
                        index=i,
                        finish_reason=finish_reasons[i],
                        message=ChatCompletionMessage(
                            role="assistant",
                            content=response_contents[i],
                            function_call=full_function_call,
                            tool_calls=full_tool_calls,
                        ),
                        logprobs=None,
                    )
                else:
                    # OpenAI versions below 1.5.0
                    choice = Choice(  # type: ignore [call-arg]
                        index=i,
                        finish_reason=finish_reasons[i],
                        message=ChatCompletionMessage(
                            role="assistant",
                            content=response_contents[i],
                            function_call=full_function_call,
                            tool_calls=full_tool_calls,
                        ),
                    )

                response.choices.append(choice)
        else:
            # If streaming is not enabled, send a regular chat completion request
            params = params.copy()
            params["stream"] = False
            response = completions.create(**params)

        return response

    def _update_usage_summary(self, response: Union[ChatCompletion, Completion], use_cache: bool) -> None:
        """Update the usage summary.

        Usage is calculated no matter filter is passed or not.
        """
        try:
            usage = response.usage
            assert usage is not None
            usage.prompt_tokens = 0 if usage.prompt_tokens is None else usage.prompt_tokens
            usage.completion_tokens = 0 if usage.completion_tokens is None else usage.completion_tokens
            usage.total_tokens = 0 if usage.total_tokens is None else usage.total_tokens
        except (AttributeError, AssertionError):
            logger.debug("Usage attribute is not found in the response.", exc_info=True)
            return

        def update_usage(usage_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            if usage_summary is None:
                usage_summary = {"total_cost": response.cost}  # type: ignore [union-attr]
            else:
                usage_summary["total_cost"] += response.cost  # type: ignore [union-attr]

            usage_summary[response.model] = {
                "cost": usage_summary.get(response.model, {}).get("cost", 0) + response.cost,  # type: ignore [union-attr]
                "prompt_tokens": usage_summary.get(response.model, {}).get("prompt_tokens", 0) + usage.prompt_tokens,
                "completion_tokens": usage_summary.get(response.model, {}).get("completion_tokens", 0)
                + usage.completion_tokens,
                "total_tokens": usage_summary.get(response.model, {}).get("total_tokens", 0) + usage.total_tokens,
            }
            return usage_summary

        self.total_usage_summary = update_usage(self.total_usage_summary)
        if not use_cache:
            self.actual_usage_summary = update_usage(self.actual_usage_summary)

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""

        def print_usage(usage_summary: Optional[Dict[str, Any]], usage_type: str = "total") -> None:
            word_from_type = "including" if usage_type == "total" else "excluding"
            if usage_summary is None:
                print("No actual cost incurred (all completions are using cache).", flush=True)
                return

            print(f"Usage summary {word_from_type} cached usage: ", flush=True)
            print(f"Total cost: {round(usage_summary['total_cost'], 5)}", flush=True)
            for model, counts in usage_summary.items():
                if model == "total_cost":
                    continue  #
                print(
                    f"* Model '{model}': cost: {round(counts['cost'], 5)}, prompt_tokens: {counts['prompt_tokens']}, completion_tokens: {counts['completion_tokens']}, total_tokens: {counts['total_tokens']}",
                    flush=True,
                )

        if self.total_usage_summary is None:
            print('No usage summary. Please call "create" first.', flush=True)
            return

        if isinstance(mode, list):
            if len(mode) == 0 or len(mode) > 2:
                raise ValueError(f'Invalid mode: {mode}, choose from "actual", "total", ["actual", "total"]')
            if "actual" in mode and "total" in mode:
                mode = "both"
            elif "actual" in mode:
                mode = "actual"
            elif "total" in mode:
                mode = "total"

        print("-" * 100, flush=True)
        if mode == "both":
            print_usage(self.actual_usage_summary, "actual")
            print()
            if self.total_usage_summary != self.actual_usage_summary:
                print_usage(self.total_usage_summary, "total")
            else:
                print(
                    "All completions are non-cached: the total cost with cached completions is the same as actual cost.",
                    flush=True,
                )
        elif mode == "total":
            print_usage(self.total_usage_summary, "total")
        elif mode == "actual":
            print_usage(self.actual_usage_summary, "actual")
        else:
            raise ValueError(f'Invalid mode: {mode}, choose from "actual", "total", ["actual", "total"]')
        print("-" * 100, flush=True)

    def clear_usage_summary(self) -> None:
        """Clear the usage summary."""
        self.total_usage_summary = None
        self.actual_usage_summary = None

    def cost(self, response: Union[ChatCompletion, Completion]) -> float:
        """Calculate the cost of the response."""
        model = response.model
        if model not in OAI_PRICE1K:
            # TODO: add logging to warn that the model is not found
            logger.debug(f"Model {model} is not found. The cost will be 0.", exc_info=True)
            return 0

        n_input_tokens = response.usage.prompt_tokens  # type: ignore [union-attr]
        n_output_tokens = response.usage.completion_tokens  # type: ignore [union-attr]
        tmp_price1K = OAI_PRICE1K[model]
        # First value is input token rate, second value is output token rate
        if isinstance(tmp_price1K, tuple):
            return (tmp_price1K[0] * n_input_tokens + tmp_price1K[1] * n_output_tokens) / 1000  # type: ignore [no-any-return]
        return tmp_price1K * (n_input_tokens + n_output_tokens) / 1000  # type: ignore [operator]

    @classmethod
    def extract_text_or_completion_object(
        cls, response: Union[ChatCompletion, Completion]
    ) -> Union[List[str], List[ChatCompletionMessage]]:
        """Extract the text or ChatCompletion objects from a completion or chat response.

        Args:
            response (ChatCompletion | Completion): The response from openai.

        Returns:
            A list of text, or a list of ChatCompletion objects if function_call/tool_calls are present.
        """
        choices = response.choices
        if isinstance(response, Completion):
            return [choice.text for choice in choices]  # type: ignore [union-attr]

        if TOOL_ENABLED:
            return [  # type: ignore [return-value]
                choice.message  # type: ignore [union-attr]
                if choice.message.function_call is not None or choice.message.tool_calls is not None  # type: ignore [union-attr]
                else choice.message.content  # type: ignore [union-attr]
                for choice in choices
            ]
        else:
            return [  # type: ignore [return-value]
                choice.message if choice.message.function_call is not None else choice.message.content  # type: ignore [union-attr]
                for choice in choices
            ]


# TODO: logging
