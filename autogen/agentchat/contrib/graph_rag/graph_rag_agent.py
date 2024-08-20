from abc import ABC, abstractmethod
from typing import List

from autogen.agentchat import ConversableAgent

from .graph_store import GraphStore


class GraphRagAgent(ConversableAgent, ABC):
    """
    A graph rag agent is a conversable agent which could query graph database for answers.

    An implementing agent class would
    1. create a graph in the underlying database with input documents
    2. use the retrieve() method to retrieve information.
    3. use the retrieved information to generate and send back messages.
    """

    @abstractmethod
    def _init_db(self, input_doc: List | None = None) -> GraphStore:
        """
        This method initializes graph database with the input documents or records.
        Usually, it takes the following steps,
        1. connecting to a graph database.
        2. extract graph nodes, edges based on input data, graph schema and etc.
        3. build indexes etc.

        return: GraphStore
        """
        pass

    @abstractmethod
    def retrieve(self, question: str, **kwargs):
        """
        Retrieve answers with human readable questions.
        """
        pass

    @abstractmethod
    def add_records(self, new_records: List) -> bool:
        """
        Add new records to the underlying database and add to the graph if required.
        """
        pass
