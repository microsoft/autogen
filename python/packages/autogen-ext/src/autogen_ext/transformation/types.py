from typing import Any, Callable, Dict, Type

from autogen_core.models import LLMMessage

TransformerFunc = Callable[[LLMMessage, Dict[str, Any]], Any]
TransformerMap = Dict[Type[LLMMessage], TransformerFunc]
