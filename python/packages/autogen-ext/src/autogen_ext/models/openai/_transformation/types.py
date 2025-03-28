from typing import Any, Callable, Dict, List, Sequence, Type, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import LLMMessage
from autogen_core.models._types import FunctionExecutionResult
from openai.types.chat import ChatCompletionMessageParam

MessageParam = Union[ChatCompletionMessageParam]  # If that transformation move to global, add other message params here
TrasformerReturnType = Sequence[MessageParam]
TransformerFunc = Callable[[LLMMessage, Dict[str, Any]], TrasformerReturnType]
TransformerMap = Dict[Type[LLMMessage], TransformerFunc]

LLMMessageContent = Union[
    # SystemMessage.content
    str,
    # UserMessage.content
    List[Union[str, Image]],
    # AssistantMessage.content
    List[FunctionCall],
    # FunctionExecutionResultMessage.content
    List[FunctionExecutionResult],
]
