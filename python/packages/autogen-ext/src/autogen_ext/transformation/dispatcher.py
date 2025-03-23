from typing import Any, Callable, Dict, List
from autogen_core.models import LLMMessage

from autogen_ext.transformation import (
    # Types
    TransformerFunc,
    TransformerMap,
    BuilderMap,
    BuilderFunc,
    # Functions
    get_transformer,
)


def dispatch_transformation(
    model_family: str,
    message: LLMMessage,
    funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]],
    context: Dict[str, Any],
) -> Any:
    """
    Dispatches a transformation for a given model family.

    The transformation is selected based on the model family and the message type.

    The context dict is passed to the transformer functions.

    Returns the transformed message.
    """
    transformer_map: TransformerMap = get_transformer(model_family)
    transformer: TransformerFunc = transformer_map.get(type(message), lambda x, y: {})
    
    builder_map: BuilderMap = get_builder(model_family)
    builder: BuilderFunc = builder_map.get(type(message), lambda x, y: x)

    parts: List[Any] = [message] if isinstance(message.content, str) else message.content
    contents: List[Any] = []
    for part in parts:
        message: Any = transformer(part, context)
        contents.append(message)

    kwargs: Dict[str, Any] = {}
    for func in funcs:
        kwargs.update(func(contents, context))

    return builder(contents, kwargs)
    