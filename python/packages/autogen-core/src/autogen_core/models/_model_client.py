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

    GPT_4O = "gpt-4o"
    O1 = "o1"
    O3 = "o3"
    GPT_4 = "gpt-4"
    GPT_35 = "gpt-35"
    R1 = "r1"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_5_HAIKU = "claude-3.5-haiku"
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"
    UNKNOWN = "unknown"

    ANY: TypeAlias = Literal[
        "gpt-4o",
        "o1",
        "o3",
        "gpt-4",
        "gpt-35",
        "r1",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "claude-3-haiku",
        "claude-3-sonnet",
        "claude-3-opus",
        "claude-3.5-haiku",
        "claude-3.5-sonnet",
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
        )

    @staticmethod
    def is_gemini(family: str) -> bool:
        return family in (
            ModelFamily.GEMINI_1_5_FLASH,
            ModelFamily.GEMINI_1_5_PRO,
            ModelFamily.GEMINI_2_0_FLASH,
        )

    @staticmethod
    def is_openai(family: str) -> bool:
        return family in (
            ModelFamily.GPT_4O,
            ModelFamily.O1,
            ModelFamily.O3,
            ModelFamily.GPT_4,
            ModelFamily.GPT_35,
            ModelFamily.R1,
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
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult: ...

    @abstractmethod
    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        # None means do not override the default
        # A value means to override the client default - often specified in the constructor
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]: ...

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
