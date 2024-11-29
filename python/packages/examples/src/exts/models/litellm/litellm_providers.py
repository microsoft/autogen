from typing import Any, Dict
from ._litellm_client import LiteLlmChatCompletionClient

class OllamaChatCompletionClient(LiteLlmChatCompletionClient):
    def __init__(self, model: str, **create_args: Dict[str, Any]):
        super().__init__(provider="ollama", model=model, **create_args)


class MistralAiCompletionClient(LiteLlmChatCompletionClient):
    def __init__(self, api_key: str, model: str, **create_args):
        super().__init__(provider="mistral",model=model,api_key=api_key, **create_args)


