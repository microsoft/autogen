import logging

from mem0.memory.utils import format_entities, sanitize_relationship_for_cypher

try:
    from langchain_memgraph.graphs.memgraph import Memgraph
except ImportError:
    raise ImportError("langchain_memgraph is not installed. Please install it using pip install langchain-memgraph")

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    raise ImportError("rank_bm25 is not installed. Please install it using pip install rank-bm25")

from mem0.graphs.tools import (
    DELETE_MEMORY_STRUCT_TOOL_GRAPH,
    DELETE_MEMORY_TOOL_GRAPH,
    EXTRACT_ENTITIES_STRUCT_TOOL,
    EXTRACT_ENTITIES_TOOL,
    RELATIONS_STRUCT_TOOL,
    RELATIONS_TOOL,
)
from mem0.graphs.utils import EXTRACT_RELATIONS_PROMPT, get_delete_messages
from mem0.utils.factory import EmbedderFactory, LlmFactory

logger = logging.getLogger(__name__)


class MemoryGraph:
    def __init__(self, config):
        self.config = config
        self.graph = Memgraph(
            self.config.graph_store.config.url,
            self.config.graph_store.config.username,
            self.config.graph_store.config.password,
        )
        self.embedding_model = EmbedderFactory.create(
            self.config.embedder.provider,
            self.config.embedder.config,
            {"enable_embeddings": True},
        )

        # Default to openai if no specific provider is configured
        self.llm_provider = "openai"
        if self.config.llm and self.config.llm.provider:
            self.llm_provider = self.config.llm.provider
        if self.config.graph_store and self.config.graph_store.llm and self.config.graph_store.llm.provider:
            self.llm_provider = self.config.graph_store.llm.provider

        # Get LLM config with proper null checks
        llm_config = None
        if self.config.graph_store and self.config.graph_store.llm and hasattr(self.config.graph_store.llm, "config"):
            llm_config = self.config.graph_store.llm.config
        elif hasattr(self.config.llm, "config"):
            llm_config = self.config.llm.config
        self.llm = LlmFactory.create(self.llm_provider, llm_config)
        self.user_id = None
        self.threshold = 0.7

        # Setup Memgraph:
        # 1. Create vector index (created Entity label on all nodes)
        # 2. Create label property index for performance optimizations
        embedding_dims = self.config.embedder.config["embedding_dims"]
        index_info = self._fetch_existing_indexes()
        # Create vector index if not exists
        if not any(idx.get("index_name") == "memzero" for idx in index_info["vector_index_exists"]):
            self.graph.query(
                f"CREATE VECTOR INDEX memzero ON :Entity(embedding) WITH CONFIG {{'dimension': {embedding_dims}, 'capacity': 1000, 'metric': 'cos'}};"
            )
        # Create label+property index if not exists
        if not any(
            idx.get("index type") == "label+property" and idx.get("label") == "Entity"
            for idx in index_info["index_exists"]
        ):
            self.graph.query("CREATE INDEX ON :Entity(user_id);")
        # Create label index if not exists
        if not any(
            idx.get("index type") == "label" and idx.get("label") == "Entity" for idx in index_info["index_exists"]
        ):
            self.graph.query("CREATE INDEX ON :Entity;")

    def add(self, data, filters):
        """
        Adds data to the graph.

        Args:
            data (str): The data to add to the graph.
            filters (dict): A dictionary containing filters to be applied during the addition.
        """
        entity_type_map = self._retrieve_nodes_from_data(data, filters)
        to_be_added = self._establish_nodes_relations_from_data(data, filters, entity_type_map)
        search_output = self._search_graph_db(node_list=list(entity_type_map.keys()), filters=filters)
        to_be_deleted = self._get_delete_entities_from_search_output(search_output, data, filters)

        # TODO: Batch queries with APOC plugin
        # TODO: Add more filter support
        deleted_entities = self._delete_entities(to_be_deleted, filters)
        added_entities = self._add_entities(to_be_added, filters, entity_type_map)

        return {"deleted_entities": deleted_entities, "added_entities": added_entities}

    def search(self, query, filters, limit=100):
        """
        Search for memories and related graph data.

        Args:
            query (str): Query to search for.
            filters (dict): A dictionary containing filters to be applied during the search.
            limit (int): The maximum number of nodes and relationships to retrieve. Defaults to 100.

        Returns:
            dict: A dictionary containing:
                - "contexts": List of search results from the base data store.
                - "entities": List of related graph data based on the query.
        """
        entity_type_map = self._retrieve_nodes_from_data(query, filters)
        search_output = self._search_graph_db(node_list=list(entity_type_map.keys()), filters=filters)

        if not search_output:
            return []

        search_outputs_sequence = [
            [item["source"], item["relationship"], item["destination"]] for item in search_output
        ]
        bm25 = BM25Okapi(search_outputs_sequence)

        tokenized_query = query.split(" ")
        reranked_results = bm25.get_top_n(tokenized_query, search_outputs_sequence, n=5)

        search_results = []
        for item in reranked_results:
            search_results.append({"source": item[0], "relationship": item[1], "destination": item[2]})

        logger.info(f"Returned {len(search_results)} search results")

        return search_results

    def delete_all(self, filters):
        """Delete all nodes and relationships for a user or specific agent."""
        if filters.get("agent_id"):
            cypher = """
            MATCH (n:Entity {user_id: $user_id, agent_id: $agent_id})
            DETACH DELETE n
            """
            params = {"user_id": filters["user_id"], "agent_id": filters["agent_id"]}
        else:
            cypher = """
            MATCH (n:Entity {user_id: $user_id})
            DETACH DELETE n
            """
            params = {"user_id": filters["user_id"]}
        self.graph.query(cypher, params=params)

    def get_all(self, filters, limit=100):
        """
        Retrieves all nodes and relationships from the graph database based on optional filtering criteria.

        Args:
            filters (dict): A dictionary containing filters to be applied during the retrieval.
                Supports 'user_id' (required) and 'agent_id' (optional).
            limit (int): The maximum number of nodes and relationships to retrieve. Defaults to 100.
        Returns:
            list: A list of dictionaries, each containing:
                - 'source': The source node name.
                - 'relationship': The relationship type.
                - 'target': The target node name.
        """
        # Build query based on whether agent_id is provided
        if filters.get("agent_id"):
            query = """
            MATCH (n:Entity {user_id: $user_id, agent_id: $agent_id})-[r]->(m:Entity {user_id: $user_id, agent_id: $agent_id})
            RETURN n.name AS source, type(r) AS relationship, m.name AS target
            LIMIT $limit
            """
            params = {"user_id": filters["user_id"], "agent_id": filters["agent_id"], "limit": limit}
        else:
            query = """
            MATCH (n:Entity {user_id: $user_id})-[r]->(m:Entity {user_id: $user_id})
            RETURN n.name AS source, type(r) AS relationship, m.name AS target
            LIMIT $limit
            """
            params = {"user_id": filters["user_id"], "limit": limit}

        results = self.graph.query(query, params=params)

        final_results = []
        for result in results:
            final_results.append(
                {
                    "source": result["source"],
                    "relationship": result["relationship"],
                    "target": result["target"],
                }
            )

        logger.info(f"Retrieved {len(final_results)} relationships")

        return final_results

    def _retrieve_nodes_from_data(self, data, filters):
        """Extracts all the entities mentioned in the query."""
        _tools = [EXTRACT_ENTITIES_TOOL]
        if self.llm_provider in ["azure_openai_structured", "openai_structured"]:
            _tools = [EXTRACT_ENTITIES_STRUCT_TOOL]
        search_results = self.llm.generate_response(
            messages=[
                {
                    "role": "system",
                    "content": f"You are a smart assistant who understands entities and their types in a given text. If user message contains self reference such as 'I', 'me', 'my' etc. then use {filters['user_id']} as the source entity. Extract all the entities from the text. ***DO NOT*** answer the question itself if the given text is a question.",
                },
                {"role": "user", "content": data},
            ],
            tools=_tools,
        )

        entity_type_map = {}

        try:
            for tool_call in search_results["tool_calls"]:
                if tool_call["name"] != "extract_entities":
                    continue
                for item in tool_call["arguments"]["entities"]:
                    entity_type_map[item["entity"]] = item["entity_type"]
        except Exception as e:
            logger.exception(
                f"Error in search tool: {e}, llm_provider={self.llm_provider}, search_results={search_results}"
            )

        entity_type_map = {k.lower().replace(" ", "_"): v.lower().replace(" ", "_") for k, v in entity_type_map.items()}
        logger.debug(f"Entity type map: {entity_type_map}\n search_results={search_results}")
        return entity_type_map

    def _establish_nodes_relations_from_data(self, data, filters, entity_type_map):
        """Eshtablish relations among the extracted nodes."""
        if self.config.graph_store.custom_prompt:
            messages = [
                {
                    "role": "system",
                    "content": EXTRACT_RELATIONS_PROMPT.replace("USER_ID", filters["user_id"]).replace(
                        "CUSTOM_PROMPT", f"4. {self.config.graph_store.custom_prompt}"
                    ),
                },
                {"role": "user", "content": data},
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": EXTRACT_RELATIONS_PROMPT.replace("USER_ID", filters["user_id"]),
                },
                {
                    "role": "user",
                    "content": f"List of entities: {list(entity_type_map.keys())}. \n\nText: {data}",
                },
            ]

        _tools = [RELATIONS_TOOL]
        if self.llm_provider in ["azure_openai_structured", "openai_structured"]:
            _tools = [RELATIONS_STRUCT_TOOL]

        extracted_entities = self.llm.generate_response(
            messages=messages,
            tools=_tools,
        )

        entities = []
        if extracted_entities["tool_calls"]:
            entities = extracted_entities["tool_calls"][0]["arguments"]["entities"]

        entities = self._remove_spaces_from_entities(entities)
        logger.debug(f"Extracted entities: {entities}")
        return entities

    def _search_graph_db(self, node_list, filters, limit=100):
        """Search similar nodes among and their respective incoming and outgoing relations."""
        result_relations = []

        for node in node_list:
            n_embedding = self.embedding_model.embed(node)

            # Build query based on whether agent_id is provided
            if filters.get("agent_id"):
                cypher_query = """
                MATCH (n:Entity {user_id: $user_id, agent_id: $agent_id})
                WHERE n.embedding IS NOT NULL
                WITH n, $n_embedding as n_embedding
                CALL node_similarity.cosine_pairwise("embedding", [n_embedding], [n.embedding])
                YIELD node1, node2, similarity
                WITH n, similarity
                WHERE similarity >= $threshold
                MATCH (n)-[r]->(m:Entity)
                RETURN n.name AS source, id(n) AS source_id, type(r) AS relationship, id(r) AS relation_id, m.name AS destination, id(m) AS destination_id, similarity
                UNION
                MATCH (n:Entity {user_id: $user_id, agent_id: $agent_id})
                WHERE n.embedding IS NOT NULL
                WITH n, $n_embedding as n_embedding
                CALL node_similarity.cosine_pairwise("embedding", [n_embedding], [n.embedding])
                YIELD node1, node2, similarity
                WITH n, similarity
                WHERE similarity >= $threshold
                MATCH (m:Entity)-[r]->(n)
                RETURN m.name AS source, id(m) AS source_id, type(r) AS relationship, id(r) AS relation_id, n.name AS destination, id(n) AS destination_id, similarity
                ORDER BY similarity DESC
                LIMIT $limit;
                """
                params = {
                    "n_embedding": n_embedding,
                    "threshold": self.threshold,
                    "user_id": filters["user_id"],
                    "agent_id": filters["agent_id"],
                    "limit": limit,
                }
            else:
                cypher_query = """
                MATCH (n:Entity {user_id: $user_id})
                WHERE n.embedding IS NOT NULL
                WITH n, $n_embedding as n_embedding
                CALL node_similarity.cosine_pairwise("embedding", [n_embedding], [n.embedding])
                YIELD node1, node2, similarity
                WITH n, similarity
                WHERE similarity >= $threshold
                MATCH (n)-[r]->(m:Entity)
                RETURN n.name AS source, id(n) AS source_id, type(r) AS relationship, id(r) AS relation_id, m.name AS destination, id(m) AS destination_id, similarity
                UNION
                MATCH (n:Entity {user_id: $user_id})
                WHERE n.embedding IS NOT NULL
                WITH n, $n_embedding as n_embedding
                CALL node_similarity.cosine_pairwise("embedding", [n_embedding], [n.embedding])
                YIELD node1, node2, similarity
                WITH n, similarity
                WHERE similarity >= $threshold
                MATCH (m:Entity)-[r]->(n)
                RETURN m.name AS source, id(m) AS source_id, type(r) AS relationship, id(r) AS relation_id, n.name AS destination, id(n) AS destination_id, similarity
                ORDER BY similarity DESC
                LIMIT $limit;
                """
                params = {
                    "n_embedding": n_embedding,
                    "threshold": self.threshold,
                    "user_id": filters["user_id"],
                    "limit": limit,
                }

            ans = self.graph.query(cypher_query, params=params)
            result_relations.extend(ans)

        return result_relations

    def _get_delete_entities_from_search_output(self, search_output, data, filters):
        """Get the entities to be deleted from the search output."""
        search_output_string = format_entities(search_output)
        system_prompt, user_prompt = get_delete_messages(search_output_string, data, filters["user_id"])

        _tools = [DELETE_MEMORY_TOOL_GRAPH]
        if self.llm_provider in ["azure_openai_structured", "openai_structured"]:
            _tools = [
                DELETE_MEMORY_STRUCT_TOOL_GRAPH,
            ]

        memory_updates = self.llm.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=_tools,
        )
        to_be_deleted = []
        for item in memory_updates["tool_calls"]:
            if item["name"] == "delete_graph_memory":
                to_be_deleted.append(item["arguments"])
        # in case if it is not in the correct format
        to_be_deleted = self._remove_spaces_from_entities(to_be_deleted)
        logger.debug(f"Deleted relationships: {to_be_deleted}")
        return to_be_deleted

    def _delete_entities(self, to_be_deleted, filters):
        """Delete the entities from the graph."""
        user_id = filters["user_id"]
        agent_id = filters.get("agent_id", None)
        results = []

        for item in to_be_deleted:
            source = item["source"]
            destination = item["destination"]
            relationship = item["relationship"]

            # Build the agent filter for the query
            agent_filter = ""
            params = {
                "source_name": source,
                "dest_name": destination,
                "user_id": user_id,
            }

            if agent_id:
                agent_filter = "AND n.agent_id = $agent_id AND m.agent_id = $agent_id"
                params["agent_id"] = agent_id

            # Delete the specific relationship between nodes
            cypher = f"""
            MATCH (n:Entity {{name: $source_name, user_id: $user_id}})
            -[r:{relationship}]->
            (m:Entity {{name: $dest_name, user_id: $user_id}})
            WHERE 1=1 {agent_filter}
            DELETE r
            RETURN 
                n.name AS source,
                m.name AS target,
                type(r) AS relationship
            """

            result = self.graph.query(cypher, params=params)
            results.append(result)

        return results

    # added Entity label to all nodes for vector search to work
    def _add_entities(self, to_be_added, filters, entity_type_map):
        """Add the new entities to the graph. Merge the nodes if they already exist."""
        user_id = filters["user_id"]
        agent_id = filters.get("agent_id", None)
        results = []

        for item in to_be_added:
            # entities
            source = item["source"]
            destination = item["destination"]
            relationship = item["relationship"]

            # types
            source_type = entity_type_map.get(source, "__User__")
            destination_type = entity_type_map.get(destination, "__User__")

            # embeddings
            source_embedding = self.embedding_model.embed(source)
            dest_embedding = self.embedding_model.embed(destination)

            # search for the nodes with the closest embeddings
            source_node_search_result = self._search_source_node(source_embedding, filters, threshold=0.9)
            destination_node_search_result = self._search_destination_node(dest_embedding, filters, threshold=0.9)

            # Prepare agent_id for node creation
            agent_id_clause = ""
            if agent_id:
                agent_id_clause = ", agent_id: $agent_id"

            # TODO: Create a cypher query and common params for all the cases
            if not destination_node_search_result and source_node_search_result:
                cypher = f"""
                    MATCH (source:Entity)
                    WHERE id(source) = $source_id
                    MERGE (destination:{destination_type}:Entity {{name: $destination_name, user_id: $user_id{agent_id_clause}}})
                    ON CREATE SET
                        destination.created = timestamp(),
                        destination.embedding = $destination_embedding,
                        destination:Entity
                    MERGE (source)-[r:{relationship}]->(destination)
                    ON CREATE SET 
                        r.created = timestamp()
                    RETURN source.name AS source, type(r) AS relationship, destination.name AS target
                    """

                params = {
                    "source_id": source_node_search_result[0]["id(source_candidate)"],
                    "destination_name": destination,
                    "destination_embedding": dest_embedding,
                    "user_id": user_id,
                }
                if agent_id:
                    params["agent_id"] = agent_id

            elif destination_node_search_result and not source_node_search_result:
                cypher = f"""
                    MATCH (destination:Entity)
                    WHERE id(destination) = $destination_id
                    MERGE (source:{source_type}:Entity {{name: $source_name, user_id: $user_id{agent_id_clause}}})
                    ON CREATE SET
                        source.created = timestamp(),
                        source.embedding = $source_embedding,
                        source:Entity
                    MERGE (source)-[r:{relationship}]->(destination)
                    ON CREATE SET 
                        r.created = timestamp()
                    RETURN source.name AS source, type(r) AS relationship, destination.name AS target
                    """

                params = {
                    "destination_id": destination_node_search_result[0]["id(destination_candidate)"],
                    "source_name": source,
                    "source_embedding": source_embedding,
                    "user_id": user_id,
                }
                if agent_id:
                    params["agent_id"] = agent_id

            elif source_node_search_result and destination_node_search_result:
                cypher = f"""
                    MATCH (source:Entity)
                    WHERE id(source) = $source_id
                    MATCH (destination:Entity)
                    WHERE id(destination) = $destination_id
                    MERGE (source)-[r:{relationship}]->(destination)
                    ON CREATE SET 
                        r.created_at = timestamp(),
                        r.updated_at = timestamp()
                    RETURN source.name AS source, type(r) AS relationship, destination.name AS target
                    """
                params = {
                    "source_id": source_node_search_result[0]["id(source_candidate)"],
                    "destination_id": destination_node_search_result[0]["id(destination_candidate)"],
                    "user_id": user_id,
                }
                if agent_id:
                    params["agent_id"] = agent_id

            else:
                cypher = f"""
                    MERGE (n:{source_type}:Entity {{name: $source_name, user_id: $user_id{agent_id_clause}}})
                    ON CREATE SET n.created = timestamp(), n.embedding = $source_embedding, n:Entity
                    ON MATCH SET n.embedding = $source_embedding
                    MERGE (m:{destination_type}:Entity {{name: $dest_name, user_id: $user_id{agent_id_clause}}})
                    ON CREATE SET m.created = timestamp(), m.embedding = $dest_embedding, m:Entity
                    ON MATCH SET m.embedding = $dest_embedding
                    MERGE (n)-[rel:{relationship}]->(m)
                    ON CREATE SET rel.created = timestamp()
                    RETURN n.name AS source, type(rel) AS relationship, m.name AS target
                    """
                params = {
                    "source_name": source,
                    "dest_name": destination,
                    "source_embedding": source_embedding,
                    "dest_embedding": dest_embedding,
                    "user_id": user_id,
                }
                if agent_id:
                    params["agent_id"] = agent_id

            result = self.graph.query(cypher, params=params)
            results.append(result)
        return results

    def _remove_spaces_from_entities(self, entity_list):
        for item in entity_list:
            item["source"] = item["source"].lower().replace(" ", "_")
            # Use the sanitization function for relationships to handle special characters
            item["relationship"] = sanitize_relationship_for_cypher(item["relationship"].lower().replace(" ", "_"))
            item["destination"] = item["destination"].lower().replace(" ", "_")
        return entity_list

    def _search_source_node(self, source_embedding, filters, threshold=0.9):
        """Search for source nodes with similar embeddings."""
        user_id = filters["user_id"]
        agent_id = filters.get("agent_id", None)

        if agent_id:
            cypher = """
                CALL vector_search.search("memzero", 1, $source_embedding) 
                YIELD distance, node, similarity
                WITH node AS source_candidate, similarity
                WHERE source_candidate.user_id = $user_id 
                AND source_candidate.agent_id = $agent_id 
                AND similarity >= $threshold
                RETURN id(source_candidate);
                """
            params = {
                "source_embedding": source_embedding,
                "user_id": user_id,
                "agent_id": agent_id,
                "threshold": threshold,
            }
        else:
            cypher = """
                CALL vector_search.search("memzero", 1, $source_embedding) 
                YIELD distance, node, similarity
                WITH node AS source_candidate, similarity
                WHERE source_candidate.user_id = $user_id 
                AND similarity >= $threshold
                RETURN id(source_candidate);
                """
            params = {
                "source_embedding": source_embedding,
                "user_id": user_id,
                "threshold": threshold,
            }

        result = self.graph.query(cypher, params=params)
        return result

    def _search_destination_node(self, destination_embedding, filters, threshold=0.9):
        """Search for destination nodes with similar embeddings."""
        user_id = filters["user_id"]
        agent_id = filters.get("agent_id", None)

        if agent_id:
            cypher = """
                CALL vector_search.search("memzero", 1, $destination_embedding) 
                YIELD distance, node, similarity
                WITH node AS destination_candidate, similarity
                WHERE node.user_id = $user_id 
                AND node.agent_id = $agent_id 
                AND similarity >= $threshold
                RETURN id(destination_candidate);
                """
            params = {
                "destination_embedding": destination_embedding,
                "user_id": user_id,
                "agent_id": agent_id,
                "threshold": threshold,
            }
        else:
            cypher = """
                CALL vector_search.search("memzero", 1, $destination_embedding) 
                YIELD distance, node, similarity
                WITH node AS destination_candidate, similarity
                WHERE node.user_id = $user_id 
                AND similarity >= $threshold
                RETURN id(destination_candidate);
                """
            params = {
                "destination_embedding": destination_embedding,
                "user_id": user_id,
                "threshold": threshold,
            }

        result = self.graph.query(cypher, params=params)
        return result

    def _fetch_existing_indexes(self):
        """
        Retrieves information about existing indexes and vector indexes in the Memgraph database.

        Returns:
            dict: A dictionary containing lists of existing indexes and vector indexes.
        """

        index_exists = list(self.graph.query("SHOW INDEX INFO;"))
        vector_index_exists = list(self.graph.query("SHOW VECTOR INDEX INFO;"))
        return {"index_exists": index_exists, "vector_index_exists": vector_index_exists}
