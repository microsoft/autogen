from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Literal, Mapping, Optional, Sequence, TypeAlias

from pydantic import BaseModel
from typing_extensions import Any, AsyncGenerator, Required, TypedDict, Union, deprecated

from .. import CancellationToken
from .._component_config import ComponentBase
from ..tools import Tool, ToolSchema
from ._types import CreateResult, LLMMessage, RequestUsage


class ModelFamily:
    """A model family is a group of models that share similar characteristics from a capabilities perspective. This is different to discrete supported features such as vision, function calling, and JSON output.

    This namespace class holds constants for the model families that AutoGen understands. Other families definitely exist and can be represented by a string, however, AutoGen will treat them as unknown."""

    GPT_41 = "gpt-41"
    GPT_45 = "gpt-45"
    GPT_4O = "gpt-4o"
    O1 = "o1"
    O3 = "o3"
    O4 = "o4"
    GPT_4 = "gpt-4"
    GPT_35 = "gpt-35"
    R1 = "r1"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet"
    LLAMA_3_3_8B = "llama-3.3-8b" 
    LLAMA_3_3_70B = "llama-3.3-70b"
    LLAMA_4_SCOUT = "llama-4-scout"
    LLAMA_4_MAVERICK = "llama-4-maverick"
    CODESRAL = "codestral"
    OPEN_CODESRAL_MAMBA = "open-codestral-mamba"
    MISTRAL = "mistral"
    MINISTRAL = "ministral"
    PIXTRAL = "pixtral"
    UNKNOWN = "unknown"

    ANY: TypeAlias = Literal[
        # openai_models
        "gpt-41",
        "gpt-45",
        "gpt-4o",
        "o1",
        "o3",
        "o4",
        "gpt-4",
        "gpt-35",
        "r1",
        # google_models
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        # anthropic_models
        "claude-3-haiku",
        "claude-3-sonnet",
        "claude-3-opus",
        "claude-3-5-haiku",
        "claude-3-5-sonnet",
        "claude-3-7-sonnet",
        # llama_models
        "llama-3.3-8b",
        "llama-3.3-70b",
        "llama-4-scout",
        "llama-4-maverick",
        # mistral_models
        "codestral",
        "open-codestral-mamba",
        "mistral",
        "ministral",
        "pixtral",
        # unknown
        "unknown",
    ]

    def __new__(cls, *args: Any, **kwargs: Any) -> ModelFamily:
        raise TypeError(f"{cls.__name__} is a namespace class and cannot be instantiated.")

    @staticmethod
    def is_claude(family: str) -> bool:
        return family in (
            ModelFamily.CLAUDE_3_HAIKU,
            ModelFamily.CLAUDE_3_SONNET,
            ModelFamily.CLAUDE_3_OPUS,
            ModelFamily.CLAUDE_3_5_HAIKU,
            ModelFamily.CLAUDE_3_5_SONNET,
            ModelFamily.CLAUDE_3_7_SONNET,
        )

    @staticmethod
    def is_gemini(family: str) -> bool:
        return family in (
            ModelFamily.GEMINI_1_5_FLASH,
            ModelFamily.GEMINI_1_5_PRO,
            ModelFamily.GEMINI_2_0_FLASH,
            ModelFamily.GEMINI_2_5_PRO,
        )

    @staticmethod
    def is_openai(family: str) -> bool:
        return family in (
            ModelFamily.GPT_45,
            ModelFamily.GPT_41,
            ModelFamily.GPT_4O,
            ModelFamily.O1,
            ModelFamily.O3,
            ModelFamily.O4,
            ModelFamily.GPT_4,
            ModelFamily.GPT_35,
        )

    @staticmethod
    def is_llama(family: str) -> bool:
        return family in (
            ModelFamily.LLAMA_3_3_8B,
            ModelFamily.LLAMA_3_3_70B,
            ModelFamily.LLAMA_4_SCOUT,
            ModelFamily.LLAMA_4_MAVERICK,
        )
    
    @staticmethod
    def is_mistral(family: str) -> bool:
        return family in (
            ModelFamily.CODESRAL,
            ModelFamily.OPEN_CODESRAL_MAMBA,
            ModelFamily.MISTRAL,
            ModelFamily.MINISTRAL,
            ModelFamily.PIXTRAL,
        )

@deprecated("Use the ModelInfo class instead ModelCapabilities.")
class ModelCapabilities(TypedDict, total=False):
    vision: Required[bool]
    function_calling: Required[bool]
    json_output: Required[bool]


class ModelInfo(TypedDict, total=False):
    """ModelInfo is a dictionary that contains information about a model's properties.
    It is expected to be used in the model_info property of a model client.

    We are expecting this to grow over time as we add more features.
    """

    vision: Required[bool]
    """True if the model supports vision, aka image input, otherwise False."""
    function_calling: Required[bool]
    """True if the model supports function calling, otherwise False."""
    json_output: Required[bool]
    """True if the model supports json output, otherwise False. Note: this is different to structured json."""
    family: Required[ModelFamily.ANY | str]
    """Model family should be one of the constants from :py:class:`ModelFamily` or a string representing an unknown model family."""
    structured_output: Required[bool]
    """True if the model supports structured output, otherwise False. This is different to json_output."""
    multiple_system_messages: Optional[bool]
    """True if the model supports multiple, non-consecutive system messages, otherwise False."""


def validate_model_info(model_info: ModelInfo) -> None:
    """Validates the model info dictionary.

    Raises:
        ValueError: If the model info dictionary is missing required fields.
    """
    required_fields = ["vision", "function_calling", "json_output", "family"]
    for field in required_fields:
        if field not in model_info:
            raise ValueError(
                f"Missing required field '{field}' in ModelInfo. "
                "Starting in v0.4.7, the required fields are enforced."
            )
    new_required_fields = ["structured_output"]
    for field in new_required_fields:
        if field not in model_info:
            warnings.warn(
                f"Missing required field '{field}' in ModelInfo. "
                "This field will be required in a future version of AutoGen.",
                UserWarning,
                stacklevel=2,
            )


class ChatCompletionClient(ComponentBase[BaseModel], ABC):
    # Caching has to be handled internally as they can depend on the create args that were stored in the constructor
    @abstractmethod
    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Creates a single response from the model.

        Args:
            messages (Sequence[LLMMessage]): The messages to send to the model.
            tools (Sequence[Tool | ToolSchema], optional): The tools to use with the model. Defaults to [].
            json_output (Optional[bool | type[BaseModel]], optional): Whether to use JSON mode, structured output, or neither.
                Defaults to None. If set to a `Pydantic BaseModel <https://docs.pydantic.dev/latest/usage/models/#model>`_ type,
                it will be used as the output type for structured output.
                If set to a boolean, it will be used to determine whether to use JSON mode or not.
                If set to `True`, make sure to instruct the model to produce JSON output in the instruction or prompt.
            extra_create_args (Mapping[str, Any], optional): Extra arguments to pass to the underlying client. Defaults to {}.
            cancellation_token (Optional[CancellationToken], optional): A token for cancellation. Defaults to None.

        Returns:
            CreateResult: The result of the model call.
        """
        ...

    @abstractmethod
    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Creates a stream of string chunks from the model ending with a CreateResult.

        Args:
            messages (Sequence[LLMMessage]): The messages to send to the model.
            tools (Sequence[Tool | ToolSchema], optional): The tools to use with the model. Defaults to [].
            json_output (Optional[bool | type[BaseModel]], optional): Whether to use JSON mode, structured output, or neither.
                Defaults to None. If set to a `Pydantic BaseModel <https://docs.pydantic.dev/latest/usage/models/#model>`_ type,
                it will be used as the output type for structured output.
                If set to a boolean, it will be used to determine whether to use JSON mode or not.
                If set to `True`, make sure to instruct the model to produce JSON output in the instruction or prompt.
            extra_create_args (Mapping[str, Any], optional): Extra arguments to pass to the underlying client. Defaults to {}.
            cancellation_token (Optional[CancellationToken], optional): A token for cancellation. Defaults to None.

        Returns:
            AsyncGenerator[Union[str, CreateResult], None]: A generator that yields string chunks and ends with a :py:class:`CreateResult`.
        """
        ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def actual_usage(self) -> RequestUsage: ...

    @abstractmethod
    def total_usage(self) -> RequestUsage: ...

    @abstractmethod
    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    @abstractmethod
    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int: ...

    # Deprecated
    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities: ...  # type: ignore

    @property
    @abstractmethod
    def model_info(self) -> ModelInfo:
        warnings.warn(
            "Model client in use does not implement model_info property. Falling back to capabilities property. The capabilities property is deprecated and will be removed soon, please implement model_info instead in the model client class.",
            stacklevel=2,
        )
        base_info: ModelInfo = self.capabilities  # type: ignore
        base_info["family"] = ModelFamily.UNKNOWN
        return base_info
