from typing import List, Protocol

from autogen.agentchat import ConversableAgent

from .document import Document
from .graph_store import GraphStore


class GraphRagAgent(ConversableAgent, Protocol):
    """
    A graph rag agent is a conversable agent which could query graph database for answers.

    An implementing agent class would
    1. create a graph in the underlying database with input documents
    2. use the retrieve() method to retrieve information.
    3. use the retrieved information to generate and send back messages.

    For example,
    graph_rag_agent = GraphRagAgent(
        name="movie knowledge graph agent",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        retrieve_config={
            "docs_path": [
                "./data/movies.txt",
            ],
            "llm_config" = autogen.config_list_from_json("OAI_CONFIG_LIST")
            "database_config" = {
                "host": "127.0.0.1",
                "port": 6379,
                "table_name": "movies"
            }
        },
    )

    # initialize database (internally)
    # self._init_db(input_doc=[Document(doc) for doc in retrieve_config["docs_path"]])

    question = "Name a few actors who've played in 'The Matrix'"

    answer = graph_rag_agent.retrieve(question)

    # answer:
    # A few actors who have played in 'The Matrix' are:
    # - Keanu Reeves
    # - Laurence Fishburne
    # - Carrie-Anne Moss
    # - Hugo Weaving
    """

    def _init_db(self, input_doc: List[Document] | None = None) -> GraphStore:
        """
        This method initializes graph database with the input documents or records.
        Usually, it takes the following steps,
        1. connecting to a graph database.
        2. extract graph nodes, edges based on input data, graph schema and etc.
        3. build indexes etc.

        Args:
        input_doc: a list of input documents that are used to build the graph in database.

        Returns: GraphStore
        """
        pass

    def retrieve(self, question: str, **kwargs):
        """
        Retrieve answers with human readable questions.
        """
        pass

    def add_records(self, new_records: List) -> bool:
        """
        Add new records to the underlying database and add to the graph if required.
        """
        pass
