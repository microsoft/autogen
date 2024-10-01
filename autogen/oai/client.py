from __future__ import annotations

import inspect
import logging
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union

from flaml.automl.logger import logger_formatter
from pydantic import BaseModel

from autogen.cache import Cache
from autogen.io.base import IOStream
from autogen.logger.logger_utils import get_current_ts
from autogen.oai.openai_utils import OAI_PRICE1K, get_key
from autogen.runtime_logging import log_chat_completion, log_new_client, log_new_wrapper, logging_enabled
from autogen.token_count_utils import count_token

from .rate_limiters import RateLimiter, TimeRateLimiter

TOOL_ENABLED = False
try:
    import openai
except ImportError:
    ERROR: Optional[ImportError] = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")
    OpenAI = object
    AzureOpenAI = object
else:
    # raises exception if openai>=1 is installed and something is wrong with imports
    from openai import APIError, APITimeoutError, AzureOpenAI, OpenAI
    from openai import __version__ as OPENAIVERSION
    from openai.resources import Completions
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice  # type: ignore [attr-defined]
    from openai.types.chat.chat_completion_chunk import (
        ChoiceDeltaFunctionCall,
        ChoiceDeltaToolCall,
        ChoiceDeltaToolCallFunction,
    )
    from openai.types.completion import Completion
    from openai.types.completion_usage import CompletionUsage

    if openai.__version__ >= "1.1.0":
        TOOL_ENABLED = True
    ERROR = None

try:
    from autogen.oai.cerebras import CerebrasClient

    cerebras_import_exception: Optional[ImportError] = None
except ImportError as e:
    cerebras_import_exception = e

try:
    from autogen.oai.gemini import GeminiClient

    gemini_import_exception: Optional[ImportError] = None
except ImportError as e:
    gemini_import_exception = e

try:
    from autogen.oai.anthropic import AnthropicClient

    anthropic_import_exception: Optional[ImportError] = None
except ImportError as e:
    anthropic_import_exception = e

try:
    from autogen.oai.mistral import MistralAIClient

    mistral_import_exception: Optional[ImportError] = None
except ImportError as e:
    mistral_import_exception = e

try:
    from autogen.oai.together import TogetherClient

    together_import_exception: Optional[ImportError] = None
except ImportError as e:
    together_import_exception = e

try:
    from autogen.oai.groq import GroqClient

    groq_import_exception: Optional[ImportError] = None
except ImportError as e:
    groq_import_exception = e

try:
    from autogen.oai.cohere import CohereClient

    cohere_import_exception: Optional[ImportError] = None
except ImportError as e:
    cohere_import_exception = e

try:
    from autogen.oai.ollama import OllamaClient

    ollama_import_exception: Optional[ImportError] = None
except ImportError as e:
    ollama_import_exception = e

try:
    from autogen.oai.bedrock import BedrockClient

    bedrock_import_exception: Optional[ImportError] = None
except ImportError as e:
    bedrock_import_exception = e

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)

LEGACY_DEFAULT_CACHE_SEED = 41
LEGACY_CACHE_DIR = ".cache"
OPEN_API_BASE_URL_PREFIX = "https://api.openai.com"


class ModelClient(Protocol):
    """
    A client class must implement the following methods:
    - create must return a response object that implements the ModelClientResponseProtocol
    - cost must return the cost of the response
    - get_usage must return a dict with the following keys:
        - prompt_tokens
        - completion_tokens
        - total_tokens
        - cost
        - model

    This class is used to create a client that can be used by OpenAIWrapper.
    The response returned from create must adhere to the ModelClientResponseProtocol but can be extended however needed.
    The message_retrieval method must be implemented to return a list of str or a list of messages from the response.
    """

    RESPONSE_USAGE_KEYS = ["prompt_tokens", "completion_tokens", "total_tokens", "cost", "model"]

    class ModelClientResponseProtocol(Protocol):
        class Choice(Protocol):
            class Message(Protocol):
                content: Optional[str]

            message: Message

        choices: List[Choice]
        model: str

    def create(self, params: Dict[str, Any]) -> ModelClientResponseProtocol: ...  # pragma: no cover

    def message_retrieval(
        self, response: ModelClientResponseProtocol
    ) -> Union[List[str], List[ModelClient.ModelClientResponseProtocol.Choice.Message]]:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        ...  # pragma: no cover

    def cost(self, response: ModelClientResponseProtocol) -> float: ...  # pragma: no cover

    @staticmethod
    def get_usage(response: ModelClientResponseProtocol) -> Dict:
        """Return usage summary of the response using RESPONSE_USAGE_KEYS."""
        ...  # pragma: no cover


class PlaceHolderClient:
    def __init__(self, config):
        self.config = config


class OpenAIClient:
    """Follows the Client protocol and wraps the OpenAI client."""

    def __init__(self, client: Union[OpenAI, AzureOpenAI]):
        self._oai_client = client

    def message_retrieval(
        self, response: Union[ChatCompletion, Completion]
    ) -> Union[List[str], List[ChatCompletionMessage]]:
        """Retrieve the messages from the response."""
        choices = response.choices
        if isinstance(response, Completion):
            return [choice.text for choice in choices]  # type: ignore [union-attr]

        if TOOL_ENABLED:
            return [  # type: ignore [return-value]
                (
                    choice.message  # type: ignore [union-attr]
                    if choice.message.function_call is not None or choice.message.tool_calls is not None  # type: ignore [union-attr]
                    else choice.message.content
                )  # type: ignore [union-attr]
                for choice in choices
            ]
        else:
            return [  # type: ignore [return-value]
                choice.message if choice.message.function_call is not None else choice.message.content  # type: ignore [union-attr]
                for choice in choices
            ]

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        """Create a completion for a given config using openai's client.

        Args:
            client: The openai client.
            params: The params for the completion.

        Returns:
            The completion.
        """
        iostream = IOStream.get_default()

        completions: Completions = (
            self._oai_client.chat.completions if "messages" in params else self._oai_client.completions
        )  # type: ignore [attr-defined]
        # If streaming is enabled and has messages, then iterate over the chunks of the response.
        if params.get("stream", False) and "messages" in params:
            response_contents = [""] * params.get("n", 1)
            finish_reasons = [""] * params.get("n", 1)
            completion_tokens = 0

            # Set the terminal text color to green
            iostream.print("\033[32m", end="")

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
                                full_function_call, completion_tokens = OpenAIWrapper._update_function_call_from_chunk(
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

                                full_tool_calls[ix], completion_tokens = OpenAIWrapper._update_tool_calls_from_chunk(
                                    tool_calls_chunk, full_tool_calls[ix], completion_tokens
                                )
                                if not content:
                                    continue

                        # End handle tool calls

                        # If content is present, print it to the terminal and update response variables
                        if content is not None:
                            iostream.print(content, end="", flush=True)
                            response_contents[choice.index] += content
                            completion_tokens += 1
                        else:
                            # iostream.print()
                            pass

            # Reset the terminal text color
            iostream.print("\033[0m\n")

            # Prepare the final ChatCompletion object based on the accumulated data
            model = chunk.model.replace("gpt-35", "gpt-3.5")  # hack for Azure API
            try:
                prompt_tokens = count_token(params["messages"], model)
            except NotImplementedError as e:
                # Catch token calculation error if streaming with customized models.
                logger.warning(str(e))
                prompt_tokens = 0
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

    def cost(self, response: Union[ChatCompletion, Completion]) -> float:
        """Calculate the cost of the response."""
        model = response.model
        if model not in OAI_PRICE1K:
            # log warning that the model is not found
            logger.warning(
                f'Model {model} is not found. The cost will be 0. In your config_list, add field {{"price" : [prompt_price_per_1k, completion_token_price_per_1k]}} for customized pricing.'
            )
            return 0

        n_input_tokens = response.usage.prompt_tokens if response.usage is not None else 0  # type: ignore [union-attr]
        n_output_tokens = response.usage.completion_tokens if response.usage is not None else 0  # type: ignore [union-attr]
        if n_output_tokens is None:
            n_output_tokens = 0
        tmp_price1K = OAI_PRICE1K[model]
        # First value is input token rate, second value is output token rate
        if isinstance(tmp_price1K, tuple):
            return (tmp_price1K[0] * n_input_tokens + tmp_price1K[1] * n_output_tokens) / 1000  # type: ignore [no-any-return]
        return tmp_price1K * (n_input_tokens + n_output_tokens) / 1000  # type: ignore [operator]

    @staticmethod
    def get_usage(response: Union[ChatCompletion, Completion]) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage is not None else 0,
            "total_tokens": response.usage.total_tokens if response.usage is not None else 0,
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }


class OpenAIWrapper:
    """A wrapper class for openai client."""

    extra_kwargs = {
        "agent",
        "cache",
        "cache_seed",
        "filter_func",
        "allow_format_str_template",
        "context",
        "api_version",
        "api_type",
        "tags",
        "price",
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
                "api_version": "2024-02-01",
            },
            {
                "model": "gpt-3.5-turbo",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "api_type": "openai",
                "base_url": "https://api.openai.com/v1",
            },
            {
                "model": "llama-7B",
                "base_url": "http://127.0.0.1:8080",
            }
        ]
        ```

            base_config: base config. It can contain both keyword arguments for openai client
                and additional kwargs.
                When using OpenAI or Azure OpenAI endpoints, please specify a non-empty 'model' either in `base_config` or in each config of `config_list`.
        """

        if logging_enabled():
            log_new_wrapper(self, locals())
        openai_config, extra_kwargs = self._separate_openai_config(base_config)
        # It's OK if "model" is not provided in base_config or config_list
        # Because one can provide "model" at `create` time.

        self._clients: List[ModelClient] = []
        self._config_list: List[Dict[str, Any]] = []
        self._rate_limiters: List[Optional[RateLimiter]] = []

        if config_list:
            self._initialize_rate_limiters(config_list)

            config_list = [config.copy() for config in config_list]  # make a copy before modifying
            for config in config_list:
                self._register_default_client(config, openai_config)  # could modify the config
                self._config_list.append(
                    {**extra_kwargs, **{k: v for k, v in config.items() if k not in self.openai_kwargs}}
                )
        else:
            self._register_default_client(extra_kwargs, openai_config)
            self._config_list = [extra_kwargs]
        self.wrapper_id = id(self)

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

    def _configure_azure_openai(self, config: Dict[str, Any], openai_config: Dict[str, Any]) -> None:
        openai_config["azure_deployment"] = openai_config.get("azure_deployment", config.get("model"))
        if openai_config["azure_deployment"] is not None:
            openai_config["azure_deployment"] = openai_config["azure_deployment"].replace(".", "")
        openai_config["azure_endpoint"] = openai_config.get("azure_endpoint", openai_config.pop("base_url", None))

        # Create a default Azure token provider if requested
        if openai_config.get("azure_ad_token_provider") == "DEFAULT":
            import azure.identity

            openai_config["azure_ad_token_provider"] = azure.identity.get_bearer_token_provider(
                azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )

    def _configure_openai_config_for_bedrock(self, config: Dict[str, Any], openai_config: Dict[str, Any]) -> None:
        """Update openai_config with AWS credentials from config."""
        required_keys = ["aws_access_key", "aws_secret_key", "aws_region"]
        optional_keys = ["aws_session_token", "aws_profile_name"]
        for key in required_keys:
            if key in config:
                openai_config[key] = config[key]
        for key in optional_keys:
            if key in config:
                openai_config[key] = config[key]

    def _register_default_client(self, config: Dict[str, Any], openai_config: Dict[str, Any]) -> None:
        """Create a client with the given config to override openai_config,
        after removing extra kwargs.

        For Azure models/deployment names there's a convenience modification of model removing dots in
        the it's value (Azure deployment names can't have dots). I.e. if you have Azure deployment name
        "gpt-35-turbo" and define model "gpt-3.5-turbo" in the config the function will remove the dot
        from the name and create a client that connects to "gpt-35-turbo" Azure deployment.
        """
        openai_config = {**openai_config, **{k: v for k, v in config.items() if k in self.openai_kwargs}}
        api_type = config.get("api_type")
        model_client_cls_name = config.get("model_client_cls")
        if model_client_cls_name is not None:
            # a config for a custom client is set
            # adding placeholder until the register_model_client is called with the appropriate class
            self._clients.append(PlaceHolderClient(config))
            logger.info(
                f"Detected custom model client in config: {model_client_cls_name}, model client can not be used until register_model_client is called."
            )
            # TODO: logging for custom client
        else:
            if api_type is not None and api_type.startswith("azure"):
                self._configure_azure_openai(config, openai_config)
                client = AzureOpenAI(**openai_config)
                self._clients.append(OpenAIClient(client))
            elif api_type is not None and api_type.startswith("cerebras"):
                if cerebras_import_exception:
                    raise ImportError("Please install `cerebras_cloud_sdk` to use Cerebras OpenAI API.")
                client = CerebrasClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("google"):
                if gemini_import_exception:
                    raise ImportError("Please install `google-generativeai` to use Google OpenAI API.")
                client = GeminiClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("anthropic"):
                if "api_key" not in config:
                    self._configure_openai_config_for_bedrock(config, openai_config)
                if anthropic_import_exception:
                    raise ImportError("Please install `anthropic` to use Anthropic API.")
                client = AnthropicClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("mistral"):
                if mistral_import_exception:
                    raise ImportError("Please install `mistralai` to use the Mistral.AI API.")
                client = MistralAIClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("together"):
                if together_import_exception:
                    raise ImportError("Please install `together` to use the Together.AI API.")
                client = TogetherClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("groq"):
                if groq_import_exception:
                    raise ImportError("Please install `groq` to use the Groq API.")
                client = GroqClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("cohere"):
                if cohere_import_exception:
                    raise ImportError("Please install `cohere` to use the Cohere API.")
                client = CohereClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("ollama"):
                if ollama_import_exception:
                    raise ImportError("Please install with `[ollama]` option to use the Ollama API.")
                client = OllamaClient(**openai_config)
                self._clients.append(client)
            elif api_type is not None and api_type.startswith("bedrock"):
                self._configure_openai_config_for_bedrock(config, openai_config)
                if bedrock_import_exception:
                    raise ImportError("Please install `boto3` to use the Amazon Bedrock API.")
                client = BedrockClient(**openai_config)
                self._clients.append(client)
            else:
                client = OpenAI(**openai_config)
                self._clients.append(OpenAIClient(client))

            if logging_enabled():
                log_new_client(client, self, openai_config)

    def register_model_client(self, model_client_cls: ModelClient, **kwargs):
        """Register a model client.

        Args:
            model_client_cls: A custom client class that follows the ModelClient interface
            **kwargs: The kwargs for the custom client class to be initialized with
        """
        existing_client_class = False
        for i, client in enumerate(self._clients):
            if isinstance(client, PlaceHolderClient):
                placeholder_config = client.config

                if placeholder_config.get("model_client_cls") == model_client_cls.__name__:
                    self._clients[i] = model_client_cls(placeholder_config, **kwargs)
                    return
            elif isinstance(client, model_client_cls):
                existing_client_class = True

        if existing_client_class:
            logger.warn(
                f"Model client {model_client_cls.__name__} is already registered. Add more entries in the config_list to use multiple model clients."
            )
        else:
            raise ValueError(
                f'Model client "{model_client_cls.__name__}" is being registered but was not found in the config_list. '
                f'Please make sure to include an entry in the config_list with "model_client_cls": "{model_client_cls.__name__}"'
            )

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
                (
                    {
                        **m,
                        "content": self.instantiate(m["content"], context, allow_format_str_template),
                    }
                    if m.get("content")
                    else m
                )
                for m in messages  # type: ignore [union-attr]
            ]
        return params

    def create(self, **config: Any) -> ModelClient.ModelClientResponseProtocol:
        """Make a completion for a given config using available clients.
        Besides the kwargs allowed in openai's [or other] client, we allow the following additional kwargs.
        The config in each client will be overridden by the config.

        Args:
            - context (Dict | None): The context to instantiate the prompt or messages. Default to None.
                It needs to contain keys that are used by the prompt template or the filter function.
                E.g., `prompt="Complete the following sentence: {prefix}, context={"prefix": "Today I feel"}`.
                The actual prompt will be:
                "Complete the following sentence: Today I feel".
                More examples can be found at [templating](/docs/Use-Cases/enhanced_inference#templating).
            - cache (AbstractCache | None): A Cache object to use for response cache. Default to None.
                Note that the cache argument overrides the legacy cache_seed argument: if this argument is provided,
                then the cache_seed argument is ignored. If this argument is not provided or None,
                then the cache_seed argument is used.
            - agent (AbstractAgent | None): The object responsible for creating a completion if an agent.
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
            - api_version (str | None): The api version. Default to None. E.g., "2024-02-01".
        Raises:
            - RuntimeError: If all declared custom model clients are not registered
            - APIError: If any model client create call raises an APIError
        """
        if ERROR:
            raise ERROR
        invocation_id = str(uuid.uuid4())
        last = len(self._clients) - 1
        # Check if all configs in config list are activated
        non_activated = [
            client.config["model_client_cls"] for client in self._clients if isinstance(client, PlaceHolderClient)
        ]
        if non_activated:
            raise RuntimeError(
                f"Model client(s) {non_activated} are not activated. Please register the custom model clients using `register_model_client` or filter them out form the config list."
            )
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
            agent = extra_kwargs.get("agent")
            price = extra_kwargs.get("price", None)
            if isinstance(price, list):
                price = tuple(price)
            elif isinstance(price, float) or isinstance(price, int):
                logger.warning(
                    "Input price is a float/int. Using the same price for prompt and completion tokens. Use a list/tuple if prompt and completion token prices are different."
                )
                price = (price, price)

            total_usage = None
            actual_usage = None

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
                    request_ts = get_current_ts()

                    response: ModelClient.ModelClientResponseProtocol = cache.get(key, None)

                    if response is not None:
                        response.message_retrieval_function = client.message_retrieval
                        try:
                            response.cost  # type: ignore [attr-defined]
                        except AttributeError:
                            # update attribute if cost is not calculated
                            response.cost = client.cost(response)
                            cache.set(key, response)
                        total_usage = client.get_usage(response)

                        if logging_enabled():
                            # Log the cache hit
                            # TODO: log the config_id and pass_filter etc.
                            log_chat_completion(
                                invocation_id=invocation_id,
                                client_id=id(client),
                                wrapper_id=id(self),
                                agent=agent,
                                request=params,
                                response=response,
                                is_cached=1,
                                cost=response.cost,
                                start_time=request_ts,
                            )

                        # check the filter
                        pass_filter = filter_func is None or filter_func(context=context, response=response)
                        if pass_filter or i == last:
                            # Return the response if it passes the filter or it is the last client
                            response.config_id = i
                            response.pass_filter = pass_filter
                            self._update_usage(actual_usage=actual_usage, total_usage=total_usage)
                            return response
                        continue  # filter is not passed; try the next config
            try:
                self._throttle_api_calls(i)
                request_ts = get_current_ts()
                response = client.create(params)
            except APITimeoutError as err:
                logger.debug(f"config {i} timed out", exc_info=True)
                if i == last:
                    raise TimeoutError(
                        "OpenAI API call timed out. This could be due to congestion or too small a timeout value. The timeout can be specified by setting the 'timeout' value (in seconds) in the llm_config (if you are using agents) or the OpenAIWrapper constructor (if you are using the OpenAIWrapper directly)."
                    ) from err
            except APIError as err:
                error_code = getattr(err, "code", None)
                if logging_enabled():
                    log_chat_completion(
                        invocation_id=invocation_id,
                        client_id=id(client),
                        wrapper_id=id(self),
                        agent=agent,
                        request=params,
                        response=f"error_code:{error_code}, config {i} failed",
                        is_cached=0,
                        cost=0,
                        start_time=request_ts,
                    )

                if error_code == "content_filter":
                    # raise the error for content_filter
                    raise
                logger.debug(f"config {i} failed", exc_info=True)
                if i == last:
                    raise
            else:
                # add cost calculation before caching no matter filter is passed or not
                if price is not None:
                    response.cost = self._cost_with_customized_price(response, price)
                else:
                    response.cost = client.cost(response)
                actual_usage = client.get_usage(response)
                total_usage = actual_usage.copy() if actual_usage is not None else total_usage
                self._update_usage(actual_usage=actual_usage, total_usage=total_usage)
                if cache_client is not None:
                    # Cache the response
                    with cache_client as cache:
                        cache.set(key, response)

                if logging_enabled():
                    # TODO: log the config_id and pass_filter etc.
                    log_chat_completion(
                        invocation_id=invocation_id,
                        client_id=id(client),
                        wrapper_id=id(self),
                        agent=agent,
                        request=params,
                        response=response,
                        is_cached=0,
                        cost=response.cost,
                        start_time=request_ts,
                    )

                response.message_retrieval_function = client.message_retrieval
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
    def _cost_with_customized_price(
        response: ModelClient.ModelClientResponseProtocol, price_1k: Tuple[float, float]
    ) -> None:
        """If a customized cost is passed, overwrite the cost in the response."""
        n_input_tokens = response.usage.prompt_tokens if response.usage is not None else 0  # type: ignore [union-attr]
        n_output_tokens = response.usage.completion_tokens if response.usage is not None else 0  # type: ignore [union-attr]
        if n_output_tokens is None:
            n_output_tokens = 0
        return (n_input_tokens * price_1k[0] + n_output_tokens * price_1k[1]) / 1000

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

    def _update_usage(self, actual_usage, total_usage):
        def update_usage(usage_summary, response_usage):
            # go through RESPONSE_USAGE_KEYS and check that they are in response_usage and if not just return usage_summary
            for key in ModelClient.RESPONSE_USAGE_KEYS:
                if key not in response_usage:
                    return usage_summary

            model = response_usage["model"]
            cost = response_usage["cost"]
            prompt_tokens = response_usage["prompt_tokens"]
            completion_tokens = response_usage["completion_tokens"]
            if completion_tokens is None:
                completion_tokens = 0
            total_tokens = response_usage["total_tokens"]

            if usage_summary is None:
                usage_summary = {"total_cost": cost}
            else:
                usage_summary["total_cost"] += cost

            usage_summary[model] = {
                "cost": usage_summary.get(model, {}).get("cost", 0) + cost,
                "prompt_tokens": usage_summary.get(model, {}).get("prompt_tokens", 0) + prompt_tokens,
                "completion_tokens": usage_summary.get(model, {}).get("completion_tokens", 0) + completion_tokens,
                "total_tokens": usage_summary.get(model, {}).get("total_tokens", 0) + total_tokens,
            }
            return usage_summary

        if total_usage is not None:
            self.total_usage_summary = update_usage(self.total_usage_summary, total_usage)
        if actual_usage is not None:
            self.actual_usage_summary = update_usage(self.actual_usage_summary, actual_usage)

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""
        iostream = IOStream.get_default()

        def print_usage(usage_summary: Optional[Dict[str, Any]], usage_type: str = "total") -> None:
            word_from_type = "including" if usage_type == "total" else "excluding"
            if usage_summary is None:
                iostream.print("No actual cost incurred (all completions are using cache).", flush=True)
                return

            iostream.print(f"Usage summary {word_from_type} cached usage: ", flush=True)
            iostream.print(f"Total cost: {round(usage_summary['total_cost'], 5)}", flush=True)
            for model, counts in usage_summary.items():
                if model == "total_cost":
                    continue  #
                iostream.print(
                    f"* Model '{model}': cost: {round(counts['cost'], 5)}, prompt_tokens: {counts['prompt_tokens']}, completion_tokens: {counts['completion_tokens']}, total_tokens: {counts['total_tokens']}",
                    flush=True,
                )

        if self.total_usage_summary is None:
            iostream.print('No usage summary. Please call "create" first.', flush=True)
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

        iostream.print("-" * 100, flush=True)
        if mode == "both":
            print_usage(self.actual_usage_summary, "actual")
            iostream.print()
            if self.total_usage_summary != self.actual_usage_summary:
                print_usage(self.total_usage_summary, "total")
            else:
                iostream.print(
                    "All completions are non-cached: the total cost with cached completions is the same as actual cost.",
                    flush=True,
                )
        elif mode == "total":
            print_usage(self.total_usage_summary, "total")
        elif mode == "actual":
            print_usage(self.actual_usage_summary, "actual")
        else:
            raise ValueError(f'Invalid mode: {mode}, choose from "actual", "total", ["actual", "total"]')
        iostream.print("-" * 100, flush=True)

    def clear_usage_summary(self) -> None:
        """Clear the usage summary."""
        self.total_usage_summary = None
        self.actual_usage_summary = None

    @classmethod
    def extract_text_or_completion_object(
        cls, response: ModelClient.ModelClientResponseProtocol
    ) -> Union[List[str], List[ModelClient.ModelClientResponseProtocol.Choice.Message]]:
        """Extract the text or ChatCompletion objects from a completion or chat response.

        Args:
            response (ChatCompletion | Completion): The response from openai.

        Returns:
            A list of text, or a list of ChatCompletion objects if function_call/tool_calls are present.
        """
        return response.message_retrieval_function(response)

    def _throttle_api_calls(self, idx: int) -> None:
        """Rate limit api calls."""
        if self._rate_limiters[idx]:
            limiter = self._rate_limiters[idx]

            assert limiter is not None
            limiter.sleep()

    def _initialize_rate_limiters(self, config_list: List[Dict[str, Any]]) -> None:
        for config in config_list:
            # Instantiate the rate limiter
            if "api_rate_limit" in config:
                self._rate_limiters.append(TimeRateLimiter(config["api_rate_limit"]))
                del config["api_rate_limit"]
            else:
                self._rate_limiters.append(None)
