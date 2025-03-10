"""Gemini model support for AutoGen."""

import os
from typing import Any, AsyncGenerator, Mapping, Optional, Sequence, Union

from autogen_core import CancellationToken, Component, Image
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema
from google import genai
from typing_extensions import Self, Unpack

from autogen_ext.models.gemini.utils import can_generate_images

from .adapter import prepare_genai_contents
from .config import GeminiChatClientConfig, VertexAIChatClientConfig
from .genai_client import GeminiCallWrapper


class BaseGeminiChatClient(ChatCompletionClient, Component):
    """
    Base class for Gemini chat completion clients using direct integration with google.genai.
    Provides common implementations for create and create_stream methods.

    This class uses the google.genai client as its core component for interacting with Gemini models.
    The client is initialized by derived classes with appropriate authentication.

    Attributes:
        _client: The google.genai client instance used for API calls
        _model: The name of the Gemini model to use
        _model_info: Information about the model's capabilities
        _create_args: Default arguments for content generation
        _gemini_wrapper: The GeminiCallWrapper instance for API interactions
    """

    def __init__(self, **kwargs: Unpack[Union[GeminiChatClientConfig, VertexAIChatClientConfig]]):
        """Initialize the base Gemini chat client.

        Args:
            config: Configuration object containing model settings
            **kwargs: Additional keyword arguments
        """
        # Extract configuration from kwargs or create new config
        config = kwargs.get("config") or self.component_config_schema(**kwargs)

        # Extract generation parameters with None checks
        create_args = {
            k: v
            for k, v in {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "max_output_tokens": config.max_output_tokens,
                "candidate_count": config.candidate_count,
                "stop_sequences": config.stop_sequences,
                "safety_settings": config.safety_settings,
            }.items()
            if v is not None
        }

        # Store configuration and initialize components
        self._raw_config = config.model_dump(exclude_none=True)
        self._model_info = config.model_info
        self._model = config.model
        self._create_args = create_args
        self._genai_client: genai.Client = self._create_client(config)

    @staticmethod
    def _validate_config(
        config: Dict[str, Any],
    ) -> Union[GeminiChatClientConfig, VertexAIChatClientConfig]:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def _create_client(config: Union[GeminiChatClientConfig, VertexAIChatClientConfig]) -> genai.Client:
        raise NotImplementedError("Subclasses must implement this method")

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Create a chat completion using the Gemini model."""
        # Convert messages to google.genai content format
        genai_contents = prepare_genai_contents(messages)

        # Generate images
        if can_generate_images(model_info=self._model_info):
            # Create a generate_images_config
            # generate_images_config = create_generate_images_config(...)
            response = self._genai_client.models.generate_images(
                model=self._model,
                contents=genai_contents,
                # config=generate_images_config,
            )
            # Convert response to CreateResult
            # return CreateResult(
            #     response=response,
            #     model=self._model,
            #     model_info=self._model_info,
            #     usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
            # )
        # Generate text
        # generate_text_config = create_generate_text_config(...)
        response = self._genai_client.models.generate_content(
            model=self._model,
            contents=genai_contents,
            # config=generate_text_config,
        )
        # Convert response to CreateResult
        # return CreateResult(
        #     response=response,
        #     model=self._model,
        #     model_info=self._model_info,
        #     usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
        # )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Create a streaming chat completion using the Gemini model."""
        # Convert messages to google.genai content format
        genai_contents = prepare_genai_contents(messages)

        # Check if image generation is supported
        if can_generate_images(model_info=self._model_info):
          raise NotImplementedError("Image generation is not supported for Gemini")

        # Generate text
        # generate_text_config = create_generate_text_config(...)
        response = self._genai_client.models.generate_content_stream(
            model=self._model,
            contents=genai_contents,
            # config=generate_text_config,
        )
        # Convert response to the output format


    def count_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
    ) -> int:
        """Count tokens for the given messages and tools using the google.genai client."""
        return self._gemini_wrapper.count_tokens(messages, tools=tools)

    def remaining_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Union[Tool, ToolSchema]] = [],
    ) -> int:
        """Calculate remaining tokens based on model's token limit."""
        return self._gemini_wrapper.remaining_tokens(messages, tools=tools)

    def actual_usage(self) -> RequestUsage:
        """Return the actual usage for the last request."""
        return self._gemini_wrapper.actual_usage()

    def total_usage(self) -> RequestUsage:
        """Return the total usage across all requests."""
        return self._gemini_wrapper.total_usage()

    @property
    def model_info(self) -> ModelInfo:
        """Return the model information."""
        return self._model_info


class GeminiChatCompletionClient(BaseGeminiChatClient, Component[GeminiChatClientConfig]):
    """
    AutoGen interface for Gemini API with enhanced capabilities.

    This client provides access to Google's Gemini models through AutoGen interface with support for:
    - Long context handling
    - Vision/multimodal inputs
    - Function/tool calling
    - Structured output (JSON)
    - Robust error handling and retries
    - Token management
    - Streaming responses

    Args:
        config (Optional[GeminiClientConfig]): Configuration model
        **kwargs: Configuration parameters that match GeminiClientConfig

    Example:
        ```python
        from autogen_ext.models.gemini import GeminiChatCompletionClient

        client = GeminiChatCompletionClient(
            model="gemini-1.5-pro",
            api_key="your-api-key",  # Or use GOOGLE_API_KEY env var
            temperature=0.7,
            max_output_tokens=1000,
        )
        ```

    References:
        - https://ai.google.dev/gemini-api/docs
        - https://github.com/googleapis/python-genai
    """

    component_type = "model"
    component_config_schema = GeminiChatClientConfig

    def __init__(self, config: Optional[GeminiChatClientConfig] = None, **kwargs: Any):
        # Resolve configuration from input or environment
        config = config or GeminiChatClientConfig(**kwargs)
        api_key = config.api_key or os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("API key required via config or GOOGLE_API_KEY environment variable")

        # Initialize base functionality
        super().__init__(config=config, **kwargs)

        # Configure genai client for Gemini API
        self._genai_client = genai.Client(api_key=api_key)
        self._gemini_wrapper.set_client(self._genai_client)  # Set the client in the wrapper

    @classmethod
    def _from_config(cls, config: GeminiChatClientConfig) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)


    @staticmethod
    def _validate_config(config: GeminiChatClientConfig) -> GeminiChatClientConfig:
        if "api_key" not in config:
            raise ValueError("api_key is required for GeminiChatCompletionClient")
        return

    @staticmethod
    def _create_client(config: GeminiChatClientConfig) -> genai.Client:
        return genai.Client(api_key=config["api_key"])

    def _to_config(self) -> GeminiChatClientConfig:
        """Convert the current instance to a configuration model."""
        return GeminiChatClientConfig(**self._raw_config)


class VertexAIChatCompletionClient(BaseGeminiChatClient, Component[VertexAIChatClientConfig]):
    """
    AutoGen interface for Vertex AI Gemini models with enhanced capabilities.

    This client provides access to Google's Gemini models through Vertex AI with support for:
    - Long context handling
    - Vision/multimodal inputs
    - Function/tool calling
    - Structured output (JSON)
    - Robust error handling and retries
    - Token management
    - Streaming responses

    Args:
        config (Optional[VertexAIClientConfig]): Configuration model
        **kwargs: Configuration parameters that match VertexAIClientConfig

    Example:
        ```python
        from autogen_ext.models.gemini import VertexAIChatCompletionClient

        client = VertexAIChatCompletionClient(model="gemini-1.5-pro", project_id="your-project-id", location="us-central1")
        ```

    References:
        - https://cloud.google.com/vertex-ai
        - https://github.com/googleapis/python-genai
    """

    component_type = "model"
    component_config_schema = VertexAIChatClientConfig

    def __init__(self, config: Optional[VertexAIChatClientConfig] = None, **kwargs: Any):
        # Resolve configuration from input
        config = config or VertexAIChatClientConfig(**kwargs)
        # Initialize base functionality
        super().__init__(config=config, **kwargs)

    @classmethod
    def _from_config(cls, config: VertexAIChatClientConfig) -> Self:
        """Create an instance from a configuration model."""
        return cls(config=config)

    @staticmethod
    def _create_client(config: VertexAIChatClientConfig) -> genai.Client:
        if config["credentials"]:
            return genai.Client(
                vertexai=True,
                project=config["project_id"],
                location=config["location"],
                credentials=config["credentials"],
            )
        else:
            return genai.Client(
                vertexai=True,
                project=config["project_id"],
                location=config["location"],
            )

    def _to_config(self) -> VertexAIChatClientConfig:
        """Convert the current instance to a configuration model."""
        return VertexAIChatClientConfig(**self._raw_config)
