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
        name="graph_rag_agent",
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

    user_proxy = UserProxyAgent(
        name="user_proxy",
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        human_input_mode="ALWAYS",
    )
    user_proxy.initiate_chat(graph_rag_agent, message="Name a few actors who've played in 'The Matrix'")

    # ChatResult(
        # chat_id=None,
        # chat_history=[
            # {'content': 'Name a few actors who've played in \'The Matrix\'', 'role': 'graph_rag_agent'},
            # {'content': 'A few actors who have played in The Matrix are:
            #   - Keanu Reeves
            #   - Laurence Fishburne
            #   - Carrie-Anne Moss
            #   - Hugo Weaving',
            #   'role': 'user_proxy'},
        # ...)

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

    def add_records(self, new_records: List) -> bool:
        """
        Add new records to the underlying database and add to the graph if required.
        """
        pass
