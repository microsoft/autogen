from typing import Any, Dict
from ._litellm_client import LiteLlmChatCompletionClient
from autogen_core.components import (
    FunctionCall,
    Image,
)

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageToolCallParam
  
)
from autogen_core.components.models._types import (
    AssistantMessage,
)

class OllamaChatCompletionClient(LiteLlmChatCompletionClient):
    def __init__(self, model: str, **create_args: Dict[str, Any]):
        super().__init__(provider="ollama_chat", model=model, **create_args)
    def assistant_message_to_oai(self,
        message: AssistantMessage,
    ) -> ChatCompletionAssistantMessageParam:
        if isinstance(message.content, list):
            tool_calls=[self.func_call_to_oai(x) for x in message.content]
            return ChatCompletionAssistantMessageParam(
                tool_calls=tool_calls,
                role="assistant",
                content="",
                name=message.source,
            )
        else:
            return ChatCompletionAssistantMessageParam(
                content=message.content,
                role="assistant",
                name=message.source,
            )

class MistralAiCompletionClient(LiteLlmChatCompletionClient):
    def __init__(self, api_key: str, model: str, **create_args):
        super().__init__(provider="mistral",model=model,api_key=api_key, **create_args)


class OpenAiLikeCompletionClient(LiteLlmChatCompletionClient):
    def __init__(self,base_url:str, api_key: str, model: str, **create_args):
        super().__init__(provider="openai",base_url=base_url,model=model,api_key=api_key, **create_args)



