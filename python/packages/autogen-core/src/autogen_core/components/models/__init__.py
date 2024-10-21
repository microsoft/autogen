import importlib
import warnings
from typing import TYPE_CHECKING, Any

from ._model_client import ChatCompletionClient, ModelCapabilities
from ._types import (
    AssistantMessage,
    ChatCompletionTokenLogprob,
    CreateResult,
    FinishReasons,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
)

if TYPE_CHECKING:
    from ._openai_client import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient


__all__ = [
    "AzureOpenAIChatCompletionClient",
    "OpenAIChatCompletionClient",
    "ModelCapabilities",
    "ChatCompletionClient",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "FunctionExecutionResult",
    "FunctionExecutionResultMessage",
    "LLMMessage",
    "RequestUsage",
    "FinishReasons",
    "CreateResult",
    "TopLogprob",
    "ChatCompletionTokenLogprob",
]


def __getattr__(name: str) -> Any:
    deprecated_classes = {
        "AzureOpenAIChatCompletionClient": "autogen_ext.models.AzureOpenAIChatCompletionClient",
        "OpenAIChatCompletionClient": "autogen_ext.modelsChatCompletionClient",
    }
    if name in deprecated_classes:
        warnings.warn(
            f"{name} moved to autogen_ext. " f"Please import it from {deprecated_classes[name]}.",
            FutureWarning,
            stacklevel=2,
        )
        # Dynamically import the class from the current module
        module = importlib.import_module("._openai_client", __name__)
        attr = getattr(module, name)
        # Cache the attribute in the module's global namespace
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__} has no attribute {name}")
