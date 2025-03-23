from typing import Dict, Callable, Type, Any
from autogen_core.models import LLMMessage, ModelFamily

TransformerFunc = Callable[[LLMMessage, Dict[str, Any]], Any]
TransformerMap = Dict[Type[LLMMessage],TransformerFunc]