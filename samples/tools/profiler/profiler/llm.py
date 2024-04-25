from typing import Protocol, runtime_checkable, List, Optional
import os
import openai

from .message import OpenAIMessage


@runtime_checkable
class ChatCompletionService(Protocol):

    def create(self, messages: List[OpenAIMessage]) -> OpenAIMessage:
        pass


class OpenAIJSONService:

    MODEL = "gpt-4-turbo"

    def __init__(self, api_key: Optional[str] = None):

        if api_key is None:
            try:
                api_key = os.environ["OPENAI_API_KEY"]
            except KeyError:
                raise ValueError("Either set api_key arg or set OPENAI_API_KEY env")
        self._client = openai.Client(api_key=api_key)

    def create(self, messages: List[OpenAIMessage]) -> OpenAIMessage:
        response = self._client.chat.completions.create(
            model=self.MODEL,
            messages=[m.to_dict() for m in messages],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )
        first_choice = response.choices[0]
        return OpenAIMessage(role=first_choice.message.role, content=first_choice.message.content)
