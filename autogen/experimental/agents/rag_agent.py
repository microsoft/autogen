import os
from typing import List

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.response import Response

from ..chat_history import ChatHistoryReadOnly
from ..model_client import ModelClient
from ..types import AssistantMessage, GenerateReplyResult, Message, SystemMessage, UserMessage


class RAGAgent:

    def __init__(self, *, name: str, description: str, data_dir: str, model_client: ModelClient):
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
        self._model_client = model_client

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

        query = await _rag_reformulate_query(chat_history, self._model_client)

        response = self._query_engine.query(query)

        if isinstance(response, Response):
            str_response = response.response
            return AssistantMessage(content=str_response)
        else:
            raise ValueError("Failed to generate response")


async def _rag_reformulate_query(chat_history: ChatHistoryReadOnly, model_client: ModelClient) -> str:
    """Create a query from the chat history.

    Args:
        chat_history: The chat history.
        model_client: The model client.
    """

    all_messages: List[Message] = []
    all_messages.extend(chat_history.messages)

    # create a query from the chat history
    query = "Below is a history of messages exchanged between a user and you (the assistant):\n\n"
    for msg in all_messages:
        if isinstance(msg, UserMessage) and isinstance(msg.content, str):
            query += "user: " + msg.content + "\n"
        elif isinstance(msg, AssistantMessage) and isinstance(msg.content, str):
            query += "assistant: " + msg.content + "\n"

    query += """\n\nConsider the above the conversation and especially the last user message.
Generate 2-3 sentences that reformulate the user's intent and contain all information from
the content."""

    print(f"Query: {query}")

    system_message = "Reformulate the query based on the chat history."

    messages = [SystemMessage(content=system_message), UserMessage(content=query)]
    response = await model_client.create(messages)
    reformulated_query = response.content

    if not isinstance(reformulated_query, str):
        raise ValueError("Failed to create reformulated query")

    print(f"Reformulated query: {reformulated_query}")

    return reformulated_query
