from collections import defaultdict
from typing import Any, Callable, Dict, List, Type

from autogen_core.models import LLMMessage, ModelFamily

from .types import (
    BuilderMap,
    TransformerFunc,
    TransformerMap,
)

# Global registry of model family → message transformer map
# Each model family (e.g. "gpt-4o", "gemini-1.5-flash") maps to a dict of LLMMessage type → transformer function
MESSAGE_TRANSFORMERS: Dict[str, Dict[str, TransformerMap]] = defaultdict(dict)
MESSAGE_BUILDERS: Dict[str, BuilderMap] = {}


def build_transformer_func(
    funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]], message_param_func: Callable[..., Any]
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


def register_transformer(api: str, model_family: str, transformer_map: TransformerMap):
    """
    Registers a transformer map for a given model family.

    Example:
        register_transformer("gpt-4o", {
            UserMessage: user_message_to_oai,
            SystemMessage: system_message_to_oai,
        })
    """
    MESSAGE_TRANSFORMERS[api][model_family] = transformer_map


def get_transformer(api: str, model_family: str) -> TransformerMap:
    """
    Returns the registered transformer map for the given model family.

    This is a thin wrapper around `MESSAGE_TRANSFORMERS.get(...)`, but serves as
    an abstraction layer to allow future enhancements such as:

    - Providing fallback transformers for unknown model families
    - Injecting mock transformers during testing
    - Adding logging, metrics, or versioning later

    Keeping this as a function (instead of direct dict access) improves long-term flexibility.
    """
    transformer = MESSAGE_TRANSFORMERS.get(api, {}).get(model_family, {})
    if not transformer:
        transformer = MESSAGE_TRANSFORMERS.get("default", {}).get("default", {})

    if not transformer:
        raise ValueError(f"No transformer found for model family '{model_family}'")

    return transformer
