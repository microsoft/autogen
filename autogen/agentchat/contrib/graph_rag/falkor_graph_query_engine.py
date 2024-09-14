import os
from dataclasses import field
from typing import List

from graphrag_sdk import KnowledgeGraph, Source
from graphrag_sdk.schema import Schema

from .document import Document
from .graph_query_engine import GraphStoreQueryResult


class FalkorGraphQueryResult(GraphStoreQueryResult):
    messages: list = field(default_factory=list)


class FalkorGraphQueryEngine:
    """
    This is a wrapper for Falkor DB KnowledgeGraph.
    """

    def __init__(
        self,
        name: str,
        host: str = "127.0.0.1",
        port: int = 6379,
        username: str | None = None,
        password: str | None = None,
        model: str = "gpt-4-1106-preview",
        schema: Schema | None = None,
    ):
        """
        Initialize a Falkor DB knowledge graph.
        Please also refer to https://github.com/FalkorDB/GraphRAG-SDK/blob/main/graphrag_sdk/kg.py

        Args:
            name (str): Knowledge graph name.
            host (str): FalkorDB hostname.
            port (int): FalkorDB port number.
            username (str|None): FalkorDB username.
            password (str|None): FalkorDB password.
            model (str): OpenAI model to use for Falkor DB to build and retrieve from the graph.
            schema: Falkor DB knowledge graph schema (ontology), https://github.com/FalkorDB/GraphRAG-SDK/blob/main/graphrag_sdk/schema/schema.py
                    If None, Falkor DB will auto generate a schema from the input docs.
        """
        self.knowledge_graph = KnowledgeGraph(name, host, port, username, password, model, schema)

    def init_db(self, input_doc: List[Document] | None):
        """
        Build the knowledge graph with input documents.
        """
        sources = []
        for doc in input_doc:
            if os.path.exists(doc.path_or_url):
                sources.append(Source(doc.path_or_url))

        if sources:
            self.knowledge_graph.process_sources(sources)

    def add_records(self, new_records: List) -> bool:
        raise NotImplementedError("This method is not supported by Falkor DB SDK yet.")

    def query(self, question: str, n_results: int = 1, **kwargs) -> FalkorGraphQueryResult:
        """
        Query the knowledage graph with a question and optional message history.

        Args:
        question: a human input question.
        n_results: number of returned results.
        kwargs:
            messages: a list of message history.

        Returns: FalkorGraphQueryResult
        """
        messages = kwargs.pop("messages", [])
        answer, messages = self.knowledge_graph.ask(question, messages)
        return FalkorGraphQueryResult(answer=answer, results=[], messages=messages)
