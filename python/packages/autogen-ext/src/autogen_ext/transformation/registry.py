from typing import Dict, List, Callable, Type, Any
from autogen_core.models import LLMMessage, ModelFamily
from autogen_ext.transformation import (
    TransformerMap,
    TransformerFunc,
    BuilderMap,
)

# Global registry of model family → message transformer map
# Each model family (e.g. "gpt-4o", "gemini-1.5-flash") maps to a dict of LLMMessage type → transformer function
MESSAGE_TRANSFORMERS: Dict[str, TransformerMap] = {}
MESSAGE_BUILDERS: Dict[str, BuilderMap] = {}

def build_transformer_func(
    funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]],
    message_param_func: Callable[..., Any]
) -> TransformerFunc:
    """
    Combines multiple transformer functions into a single transformer.

    Each `func` must accept a message and a context dict, and return a partial dict
    of keyword arguments. These are merged and passed to `message_param_func`.

    This structure allows flexible transformation pipelines and future extensibility
    (e.g., prepend name, insert metadata, etc).

    message_param_func: A model-specific constructor (e.g. ChatCompletionMessageParam).
    Signature is intentionally open: Callable[..., Any].
    """
    def transformer_func(message: LLMMessage, context: Any) -> Any:
        kwargs: Dict[str, Any] = {}
        for func in funcs:
            kwargs.update(func(message, context))
        return message_param_func(**kwargs)

    return transformer_func


def build_conditional_transformer_func(
    funcs_map: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]],
    message_param_func_map: Dict[str, Callable[..., Any]],
    condition_func: Callable[[LLMMessage, Dict[str, Any]], str],
) -> TransformerFunc:
    """
    Combines multiple transformer functions into a single transformer, with a conditional constructor.

    Each `func` must accept a message and a context dict, and return a partial dict
    of keyword arguments. These are merged and passed to the constructor selected by `condition_func`.

    This structure allows flexible transformation pipelines and future extensibility
    (e.g., prepend name, insert metadata, etc).

    message_param_func_map: A mapping of condition → constructor function.
    condition_func: A function that returns the condition for selecting the constructor.
    """
    def transformer(message: LLMMessage, context: Dict[str, Any]) -> Any:
        condition = condition_func(message, context)
        constructor = message_param_func_map[condition]
        kwargs: Dict[str, Any] = {}
        for func in funcs_map[condition]:
            kwargs.update(func(message, context))
        return constructor(**kwargs)

    return transformer


def register_transformer(model_family: str, transformer_map: TransformerMap):
    """
    Registers a transformer map for a given model family.

    Example:
        register_transformer("gpt-4o", {
            UserMessage: user_message_to_oai,
            SystemMessage: system_message_to_oai,
        })
    """
    MESSAGE_TRANSFORMERS[model_family] = transformer_map


def get_transformer(model_family: str) -> TransformerMap:
    """
    Returns the registered transformer map for the given model family.
    
    This is a thin wrapper around `MESSAGE_TRANSFORMERS.get(...)`, but serves as
    an abstraction layer to allow future enhancements such as:

    - Providing fallback transformers for unknown model families
    - Injecting mock transformers during testing
    - Adding logging, metrics, or versioning later

    Keeping this as a function (instead of direct dict access) improves long-term flexibility.
    """
    return MESSAGE_TRANSFORMERS.get(model_family, {})


def register_builder(model_family: str, builder_map: BuilderMap):
    """
    Registers a builder map for a given model family.

    Example:
        register_builder("gpt-4o", {
            UserMessage: user_message_to_oai,
            SystemMessage: system_message_to_oai,
        })
    """
    MESSAGE_BUILDERS[model_family] = builder_map


def get_builder(model_family: str) -> BuilderMap:
    """
    Returns the registered builder map for the given model family.
    
    This is a thin wrapper around `MESSAGE_BUILDERS.get(...)`, but serves as
    an abstraction layer to allow future enhancements such as:

    - Providing fallback builders for unknown model families
    - Injecting mock builders during testing
    - Adding logging, metrics, or versioning later

    Keeping this as a function (instead of direct dict access) improves long-term flexibility.
    """
    return MESSAGE_BUILDERS.get(model_family, {})