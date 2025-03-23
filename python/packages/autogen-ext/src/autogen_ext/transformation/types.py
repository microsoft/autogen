from typing import Dict, List, Callable, Type, Any
from autogen_core.models import LLMMessage, ModelFamily

TransformerFunc = Callable[[LLMMessage, Dict[str, Any]], Any]
TransformerMap = Dict[Type[LLMMessage],TransformerFunc]

BuilderFunc = Callable[[List[Any], Dict[str, Any]], Any]
BuilderMap = Dict[Type[LLMMessage], BuilderFunc]
