from typing import Any, Callable, Dict, Sequence, Type, Union

from autogen_core.models import LLMMessage
from openai.types.chat import ChatCompletionMessageParam

MessageParam = Union[ChatCompletionMessageParam]  # If that transformation move to global, add other message params here
TrasformerReturnType = Sequence[MessageParam]
TransformerFunc = Callable[[LLMMessage, Dict[str, Any]], TrasformerReturnType]
TransformerMap = Dict[Type[LLMMessage], TransformerFunc]
