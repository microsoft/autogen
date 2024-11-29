
from typing import Any, Dict, Mapping, Optional, Sequence, Union
from autogen_core.components.models._model_client import ChatCompletionClient, ModelCapabilities
from autogen_core.components.models._types import (
    AssistantMessage,
    ChatCompletionTokenLogprob,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
)
from autogen_core.components.tools import Tool, ToolSchema
from ollama import Client as OllamaAi,AsyncClient as OllamaAsyncAi
from ollama import ChatResponse
from autogen_core.base import CancellationToken
from autogen_core.components import (
    FunctionCall,
    Image,
)
class OpenAIChatCompletionClient(ChatCompletionClient):

    def __init__(
        self,
        client: Union[OllamaAi,OllamaAsyncAi],
        create_args: Dict[str, Any],
        model_capabilities: Optional[ModelCapabilities] = None,
    ):
        self._ollama=client
        pass
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(**config)
    
    async def create(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        self._ollama.chat()