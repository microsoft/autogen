import os
from typing import List

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.response import Response

from ..chat_history import ChatHistoryReadOnly
from ..types import AssistantMessage, GenerateReplyResult, Message, UserMessage


class RAGAgent:

    def __init__(self, *, name: str, description: str, data_dir: str):
        """Create a RAGAgent.

        Args:
            name: The name of the agent.
            description: The description of the agent. Used for the agent's introduction in
                a group chat setting.
            data_dir: The directory containing the data for the agent.
        """
        self._name = name
        self._description = description
        self._data_dir = data_dir
        self._query_engine = None

    @property
    def name(self) -> str:
        """The name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """The description of the agent. Used for the agent's introduction in
        a group chat setting."""
        return self._description

    async def _create_query_engine(self):

        # check if OPENAI_API_KEY is set
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY is not set")

        # check if data directory exists and is not empty
        if not os.path.exists(self._data_dir):
            raise ValueError(f"Data directory {self._data_dir} does not exist")
        if not os.listdir(self._data_dir):
            raise ValueError(f"Data directory {self._data_dir} is empty")

        documents = SimpleDirectoryReader(self._data_dir).load_data()
        index = VectorStoreIndex.from_documents(documents)
        query_engine = index.as_query_engine()
        if query_engine is None:
            raise ValueError("Failed to create query engine")
        return query_engine

    async def generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:

        # create query engine if not already created
        if self._query_engine is None:
            self._query_engine = await self._create_query_engine()

        all_messages: List[Message] = []
        all_messages.extend(chat_history.messages)

        # create a query from the chat history
        query = "Below is a history of messages exchanged between a user and you (assistant):"
        for msg in all_messages[:-1]:
            if isinstance(msg, UserMessage) and isinstance(msg.content, str):
                query += "user " + msg.content + "\n"
            elif isinstance(msg, AssistantMessage) and isinstance(msg.content, str):
                query += "assistant " + msg.content + "\n"

        if isinstance(all_messages[-1], UserMessage):
            query += f"Now the user asked: {all_messages[-1].content}"

        response = self._query_engine.query(query)

        if isinstance(response, Response):
            str_response = response.response
            return AssistantMessage(content=str_response)
        else:
            raise ValueError("Failed to generate response")
