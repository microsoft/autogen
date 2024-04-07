import time
from dataclasses import dataclass
from typing import List, Protocol, runtime_checkable, Optional

import autogen


@dataclass
class OpenAIMessage:
    role: str
    content: str


@runtime_checkable
class ChatCompletionService(Protocol):

    def create(self, messages: List[OpenAIMessage]) -> OpenAIMessage:
        pass


class AutoGenChatCompletionService:

    def __init__(self, llm_config: dict):
        self._llm_config = llm_config

    def create(self, messages: list[OpenAIMessage]) -> OpenAIMessage:
        """
        Create a response message using the autogen API.

        Args:
            messages: A list of messages.

        Returns:
            A tuple containing the response message, the cost, and the duration.
        """

        if self._llm_config is None:
            self._llm_config = {"config_list": autogen.config_list_from_json("OAI_CONFIG_LIST")}

        client = autogen.OpenAIWrapper(**self._llm_config)
        autogen_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = client.create(messages=autogen_messages)

        content = client.extract_text_or_completion_object(response)[0]

        response_message = OpenAIMessage(role="assistant", content=content)
        return response_message
