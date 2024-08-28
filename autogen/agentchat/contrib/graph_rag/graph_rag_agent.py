from typing import List, Protocol

from autogen.agentchat import ConversableAgent

from .graph_query_engine import GraphQueryEngine


class GraphRagAgent(ConversableAgent, Protocol):
    """
    A graph rag agent is a conversable agent which could query graph database for answers.

    An implementing agent class would
    1. create a graph in the underlying database with input documents
    2. use the retrieve() method to retrieve information.
    3. use the retrieved information to generate and send back messages.

    For example,
    graph_query_engine = GraphQueryEngine(...)
    graph_query_engine.init_db([Document(doc1), Document(doc2), ...])

    graph_rag_agent = GraphRagAgent(
        name="graph_rag_agent",
        max_consecutive_auto_reply=3,
        ...
    )
    graph_rag_agent.attach_graph_query_engine(graph_query_engine)

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

    def attach_graph_query_engine(self, graph_query_engine: GraphQueryEngine):
        """Add a graph query engine to the agent."""
        pass
