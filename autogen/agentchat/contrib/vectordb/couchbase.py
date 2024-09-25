import json
import time
from datetime import timedelta
from typing import Any, Callable, Dict, List, Literal, Tuple, Union

import numpy as np
from couchbase import search
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster, ClusterOptions
from couchbase.collection import Collection
from couchbase.management.search import SearchIndex
from couchbase.options import SearchOptions
from couchbase.vector_search import VectorQuery, VectorSearch
from sentence_transformers import SentenceTransformer

from .base import Document, ItemID, QueryResults, VectorDB
from .utils import get_logger

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 1000
_SAMPLE_SENTENCE = ["The weather is lovely today in paradise."]
TEXT_KEY = "content"
EMBEDDING_KEY = "embedding"


class CouchbaseVectorDB(VectorDB):
    """
    A vector database implementation that uses Couchbase as the backend.
    """

    def __init__(
        self,
        connection_string: str = "couchbase://localhost",
        username: str = "Administrator",
        password: str = "password",
        bucket_name: str = "vector_db",
        embedding_function: Callable = SentenceTransformer("all-MiniLM-L6-v2").encode,
        scope_name: str = "_default",
        collection_name: str = "_default",
        index_name: str = None,
    ):
        """
        Initialize the vector database.

        Args:
            connection_string (str): The Couchbase connection string to connect to. Default is 'couchbase://localhost'.
            username (str): The username for Couchbase authentication. Default is 'Administrator'.
            password (str): The password for Couchbase authentication. Default is 'password'.
            bucket_name (str): The name of the bucket. Default is 'vector_db'.
            embedding_function (Callable): The embedding function used to generate the vector representation. Default is SentenceTransformer("all-MiniLM-L6-v2").encode.
            scope_name (str): The name of the scope. Default is '_default'.
            collection_name (str): The name of the collection to create for this vector database. Default is '_default'.
            index_name (str): Index name for the vector database. Default is None.
            overwrite (bool): Whether to overwrite existing data. Default is False.
            wait_until_index_ready (float | None): Blocking call to wait until the database indexes are ready. None means no wait. Default is None.
            wait_until_document_ready (float | None): Blocking call to wait until the database documents are ready. None means no wait. Default is None.
        """
        print(
            "CouchbaseVectorDB",
            connection_string,
            username,
            password,
            bucket_name,
            scope_name,
            collection_name,
            index_name,
        )
        self.embedding_function = embedding_function
        self.index_name = index_name

        # This will get the model dimension size by computing the embeddings dimensions
        self.dimensions = self._get_embedding_size()

        try:
            auth = PasswordAuthenticator(username, password)
            cluster = Cluster(connection_string, ClusterOptions(auth))
            cluster.wait_until_ready(timedelta(seconds=5))
            self.cluster = cluster

            self.bucket = cluster.bucket(bucket_name)
            self.scope = self.bucket.scope(scope_name)
            self.collection = self.scope.collection(collection_name)
            self.active_collection = self.collection

            logger.debug("Successfully connected to Couchbase")
        except Exception as err:
            raise ConnectionError("Could not connect to Couchbase server") from err

    def search_index_exists(self, index_name: str):
        """Check if the specified index is ready"""
        try:
            search_index_mgr = self.scope.search_indexes()
            index = search_index_mgr.get_index(index_name)
            return index.is_valid()
        except Exception:
            return False

    def _get_embedding_size(self):
        return len(self.embedding_function(_SAMPLE_SENTENCE)[0])

    def create_collection(
        self,
        collection_name: str,
        overwrite: bool = False,
        get_or_create: bool = True,
    ) -> Collection:
        """
        Create a collection in the vector database and create a vector search index in the collection.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get or create the collection. Default is True
        """
        if overwrite:
            self.delete_collection(collection_name)

        try:
            collection_mgr = self.bucket.collections()
            collection_mgr.create_collection(self.scope.name, collection_name)

        except Exception:
            if not get_or_create:
                raise ValueError(f"Collection {collection_name} already exists.")
            else:
                logger.debug(f"Collection {collection_name} already exists. Getting the collection.")

        collection = self.scope.collection(collection_name)
        self.create_index_if_not_exists(index_name=self.index_name, collection=collection)
        return collection

    def create_index_if_not_exists(self, index_name: str = "vector_index", collection=None) -> None:
        """
        Creates a vector search index on the specified collection in Couchbase.

        Args:
            index_name (str, optional): The name of the vector search index to create. Defaults to "vector_search_index".
            collection (Collection, optional): The Couchbase collection to create the index on. Defaults to None.
        """
        if not self.search_index_exists(index_name):
            self.create_vector_search_index(collection, index_name)

    def get_collection(self, collection_name: str = None) -> Collection:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Collection | The collection object.
        """
        if collection_name is None:
            if self.active_collection is None:
                raise ValueError("No collection is specified.")
            else:
                logger.debug(
                    f"No collection is specified. Using current active collection {self.active_collection.name}."
                )
        else:
            self.active_collection = self.scope.collection(collection_name)

        return self.active_collection

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.
        """
        try:
            collection_mgr = self.bucket.collections()
            collection_mgr.drop_collection(self.scope.name, collection_name)
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")

    def create_vector_search_index(
        self,
        collection,
        index_name: Union[str, None] = "vector_index",
        similarity: Literal["l2_norm", "dot_product"] = "dot_product",
    ) -> None:
        """Create a vector search index in the collection."""
        search_index_mgr = self.scope.search_indexes()
        dims = self._get_embedding_size()
        index_definition = {
            "type": "fulltext-index",
            "name": index_name,
            "sourceType": "couchbase",
            "sourceName": self.bucket.name,
            "planParams": {"maxPartitionsPerPIndex": 1024, "indexPartitions": 1},
            "params": {
                "doc_config": {
                    "docid_prefix_delim": "",
                    "docid_regexp": "",
                    "mode": "scope.collection.type_field",
                    "type_field": "type",
                },
                "mapping": {
                    "analysis": {},
                    "default_analyzer": "standard",
                    "default_datetime_parser": "dateTimeOptional",
                    "default_field": "_all",
                    "default_mapping": {"dynamic": True, "enabled": False},
                    "default_type": "_default",
                    "docvalues_dynamic": False,
                    "index_dynamic": True,
                    "store_dynamic": True,
                    "type_field": "_type",
                    "types": {
                        f"{self.scope.name}.{collection.name}": {
                            "dynamic": False,
                            "enabled": True,
                            "properties": {
                                "embedding": {
                                    "dynamic": False,
                                    "enabled": True,
                                    "fields": [
                                        {
                                            "dims": dims,
                                            "index": True,
                                            "name": "embedding",
                                            "similarity": similarity,
                                            "type": "vector",
                                            "vector_index_optimized_for": "recall",
                                        }
                                    ],
                                },
                                "metadata": {"dynamic": True, "enabled": True},
                                "content": {
                                    "dynamic": False,
                                    "enabled": True,
                                    "fields": [
                                        {
                                            "include_in_all": True,
                                            "index": True,
                                            "name": "content",
                                            "store": True,
                                            "type": "text",
                                        }
                                    ],
                                },
                            },
                        }
                    },
                },
                "store": {"indexType": "scorch", "segmentVersion": 16},
            },
            "sourceParams": {},
        }

        search_index_def = SearchIndex.from_json(json.dumps(index_definition))
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            try:
                search_index_mgr.upsert_index(search_index_def)
                break
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1}/{max_attempts}: Error creating search index: {e}")
                time.sleep(3)
                attempt += 1

        if attempt == max_attempts:
            logger.error(f"Error creating search index after {max_attempts} attempts.")
            raise RuntimeError(f"Error creating search index after {max_attempts} attempts.")

        logger.info(f"Search index {index_name} created successfully.")

    def upsert_docs(
        self, docs: List[Document], collection: Collection, batch_size=DEFAULT_BATCH_SIZE, **kwargs: Any
    ) -> None:
        if docs[0].get("content") is None:
            raise ValueError("The document content is required.")
        if docs[0].get("id") is None:
            raise ValueError("The document id is required.")

        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            docs_to_upsert = dict()
            for doc in batch:
                doc_id = doc["id"]
                embedding = self.embedding_function(
                    [doc["content"]]
                ).tolist()  # Gets new embedding even in case of document update

                doc_content = {TEXT_KEY: doc["content"], "metadata": doc.get("metadata", {}), EMBEDDING_KEY: embedding}
                docs_to_upsert[doc_id] = doc_content
            collection.upsert_multi(docs_to_upsert)

    def insert_docs(
        self,
        docs: List[Document],
        collection_name: str = None,
        upsert: bool = False,
        batch_size=DEFAULT_BATCH_SIZE,
        **kwargs,
    ) -> None:
        """Insert Documents and Vector Embeddings into the collection of the vector database. Documents are upserted in all cases."""
        if not docs:
            logger.info("No documents to insert.")
            return

        collection = self.get_collection(collection_name)
        self.upsert_docs(docs, collection, batch_size=batch_size)

    def update_docs(
        self, docs: List[Document], collection_name: str = None, batch_size=DEFAULT_BATCH_SIZE, **kwargs: Any
    ) -> None:
        """Update documents, including their embeddings, in the Collection."""
        collection = self.get_collection(collection_name)
        self.upsert_docs(docs, collection, batch_size)

    def delete_docs(self, ids: List[ItemID], collection_name: str = None, batch_size=DEFAULT_BATCH_SIZE, **kwargs):
        """Delete documents from the collection of the vector database."""
        collection = self.get_collection(collection_name)
        # based on batch size, delete the documents
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            collection.remove_multi(batch)

    def get_docs_by_ids(
        self, ids: List[ItemID] | None = None, collection_name: str = None, include: List[str] | None = None, **kwargs
    ) -> List[Document]:
        """Retrieve documents from the collection of the vector database based on the ids."""
        if include is None:
            include = [TEXT_KEY, "metadata", "id"]
        elif "id" not in include:
            include.append("id")

        collection = self.get_collection(collection_name)
        if ids is not None:
            docs = [collection.get(doc_id) for doc_id in ids]
        else:
            # Get all documents using couchbase query
            include_str = ", ".join(include)
            query = f"SELECT {include_str} FROM {self.bucket.name}.{self.scope.name}.{collection.name}"
            result = self.cluster.query(query)
            docs = []
            for row in result:
                docs.append(row)

        return [{k: v for k, v in doc.items() if k in include or k == "id"} for doc in docs]

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs,
    ) -> QueryResults:
        """Retrieve documents from the collection of the vector database based on the queries.
        Note: Distance threshold is not supported in Couchbase FTS.
        """

        results: QueryResults = []
        for query_text in queries:
            query_vector = np.array(self.embedding_function([query_text])).tolist()[0]
            query_result = self._vector_search(
                query_vector,
                n_results,
                **kwargs,
            )
            results.append(query_result)
        return results

    def _vector_search(self, embedding_vector: List[float], n_results: int = 10, **kwargs) -> List[Tuple[Dict, float]]:
        """Core vector search using Couchbase FTS."""

        search_req = search.SearchRequest.create(
            VectorSearch.from_vector_query(
                VectorQuery(
                    EMBEDDING_KEY,
                    embedding_vector,
                    n_results,
                )
            )
        )

        search_options = SearchOptions(limit=n_results, fields=["*"])
        result = self.scope.search(self.index_name, search_req, search_options)

        docs_with_score = []

        for row in result.rows():
            doc = row.fields
            doc["id"] = row.id
            score = row.score

            docs_with_score.append((doc, score))

        return docs_with_score
