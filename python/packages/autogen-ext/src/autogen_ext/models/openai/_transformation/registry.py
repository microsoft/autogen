from collections import defaultdict
from typing import Any, Callable, Dict, List, get_args

from autogen_core.models import LLMMessage, ModelFamily

from .types import (
    TransformerFunc,
    TransformerMap,
)

# Global registry of model family → message transformer map
# Each model family (e.g. "gpt-4o", "gemini-1.5-flash") maps to a dict of LLMMessage type → transformer function
MESSAGE_TRANSFORMERS: Dict[str, Dict[str, TransformerMap]] = defaultdict(dict)


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
        return [message_param_func(**kwargs)]

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
        message_param_func = message_param_func_map[condition]
        kwargs: Dict[str, Any] = {}
        for func in funcs_map[condition]:
            kwargs.update(func(message, context))
        if kwargs.get("pass_message", False):
            return []
        return [message_param_func(**kwargs)]

    return transformer


def register_transformer(api: str, model_family: str, transformer_map: TransformerMap) -> None:
    """
    Registers a transformer map for a given model family.

    Example:

        .. code-block:: python

            register_transformer(
                "gpt-4o",
                {
                    UserMessage: user_message_to_oai,
                    SystemMessage: system_message_to_oai,
                },
            )
    """
    MESSAGE_TRANSFORMERS[api][model_family] = transformer_map


def _find_model_family(api: str, model: str) -> str:
    """
    Finds the best matching model family for the given model.
    Search via prefix matching (e.g. "gpt-4o" → "gpt-4o-1.0").
    """
    len_family = 0
    family = ModelFamily.UNKNOWN
    for _family in MESSAGE_TRANSFORMERS[api].keys():
        if model.startswith(_family):
            if len(_family) > len_family:
                family = _family
                len_family = len(_family)
    return family


def get_transformer(api: str, model: str, model_family: str) -> TransformerMap:
    """
    Returns the registered transformer map for the given model family.

    This is a thin wrapper around `MESSAGE_TRANSFORMERS.get(...)`, but serves as
    an abstraction layer to allow future enhancements such as:

    - Providing fallback transformers for unknown model families
    - Injecting mock transformers during testing
    - Adding logging, metrics, or versioning later

    Keeping this as a function (instead of direct dict access) improves long-term flexibility.
    """

    if model_family not in set(get_args(ModelFamily.ANY)) or model_family == ModelFamily.UNKNOWN:
        # fallback to finding the best matching model family
        model_family = _find_model_family(api, model)

    transformer = MESSAGE_TRANSFORMERS.get(api, {}).get(model_family, {})

    if not transformer:
        # Just in case, we should never reach here
        raise ValueError(f"No transformer found for model family '{model_family}'")

    return transformer
