import os
from typing import Any, Callable, List

from .utils import get_logger

try:
    import chromadb

    if chromadb.__version__ < "0.4.15":
        raise ImportError("Please upgrade chromadb to version 0.4.15 or later.")
    from chromadb.api.models.Collection import Collection
except ImportError:
    raise ImportError("Please install chromadb: `pip install chromadb`")

CHROMADB_MAX_BATCH_SIZE = os.environ.get("CHROMADB_MAX_BATCH_SIZE", 40000)
logger = get_logger(__name__)


class ChromaVectorDB:
    """
    A vector database that uses ChromaDB as the backend.
    """

    def __init__(self, db_config: dict = None) -> None:
        """
        Initialize the vector database.

        Args:
            db_config: dict | configuration for initializing the vector database. Default is None.
                It can contain the following keys:
                client: chromadb.Client | The client object of the vector database. Default is None.
                    If not None, it will use the client object to connect to the vector database.
                path: str | The path to the vector database. Default is None.
                embedding_function: Callable | The embedding function used to generate the vector representation
                    of the documents. Default is None.
                metadata: dict | The metadata of the vector database. Default is None. If None, it will use this
                    setting: {"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32}. For more details of
                    the metadata, please refer to [distances](https://github.com/nmslib/hnswlib#supported-distances),
                    [hnsw](https://github.com/chroma-core/chroma/blob/566bc80f6c8ee29f7d99b6322654f32183c368c4/chromadb/segment/impl/vector/local_hnsw.py#L184),
                    and [ALGO_PARAMS](https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md).
                kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        if db_config is None:
            db_config = {}
        self.client = db_config.get("client")
        if not self.client:
            self.path = db_config.get("path")
            self.embedding_function = db_config.get("embedding_function")
            self.metadata = db_config.get("metadata", {"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32})
            kwargs = db_config.get("kwargs", {})
            if self.path is not None:
                self.client = chromadb.PersistentClient(path=self.path, **kwargs)
            else:
                self.client = chromadb.Client(**kwargs)
        self.active_collection = None

    def create_collection(
        self, collection_name: str, overwrite: bool = False, get_or_create: bool = True
    ) -> Collection:
        """
        Create a collection in the vector database.
        Case 1. if the collection does not exist, create the collection.
        Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
        Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
            otherwise it raise a ValueError.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True.

        Returns:
            Collection | The collection object.
        """
        try:
            collection = self.client.get_collection(collection_name)
        except ValueError:
            collection = None
        if collection is None:
            return self.client.create_collection(
                collection_name,
                embedding_function=self.embedding_function,
                get_or_create=get_or_create,
                metadata=self.metadata,
            )
        elif overwrite:
            self.client.delete_collection(collection_name)
            return self.client.create_collection(
                collection_name,
                embedding_function=self.embedding_function,
                get_or_create=get_or_create,
                metadata=self.metadata,
            )
        elif get_or_create:
            return collection
        else:
            raise ValueError(f"Collection {collection_name} already exists.")

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
                logger.info(
                    f"No collection is specified. Using current active collection {self.active_collection.name}."
                )
        else:
            self.active_collection = self.client.get_collection(collection_name)
        return self.active_collection

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            None
        """
        self.client.delete_collection(collection_name)
        if self.active_collection:
            if self.active_collection.name == collection_name:
                self.active_collection = None

    def _batch_insert(self, collection, embeddings=None, ids=None, metadata=None, documents=None, upsert=False):
        batch_size = int(CHROMADB_MAX_BATCH_SIZE)
        for i in range(0, len(documents), min(batch_size, len(documents))):
            end_idx = i + min(batch_size, len(documents) - i)
            collection_kwargs = {
                "documents": documents[i:end_idx],
                "ids": ids[i:end_idx],
                "metadatas": metadata[i:end_idx] if metadata else None,
                "embeddings": embeddings[i:end_idx] if embeddings else None,
            }
            if upsert:
                collection.upsert(**collection_kwargs)
            else:
                collection.add(**collection_kwargs)

    def insert_docs(self, docs: List[dict], collection_name: str = None, upsert: bool = False) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[dict] | A list of documents. Each document is a dictionary.
                It should include the following fields:
                    - required: "id", "content"
                    - optional: "embedding", "metadata", "distance", etc.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        if not docs:
            return
        collection = self.get_collection(collection_name)
        if docs[0].get("embedding") is None:
            logger.info(
                "No content embedding is provided. Will use the VectorDB's embedding function to generate the content embedding."
            )
            embeddings = None
        else:
            embeddings = [doc.embedding for doc in docs]
        documents = [doc.content for doc in docs]
        ids = [doc.id for doc in docs]
        metadata = [doc.get("metadata") for doc in docs]
        self._batch_insert(collection, embeddings, ids, metadata, documents, upsert)

    def update_docs(self, docs: List[dict], collection_name: str = None) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[dict] | A list of documents.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            None
        """
        self.insert_docs(docs, collection_name, upsert=True)

    def delete_docs(self, ids: List[Any], collection_name: str = None, **kwargs) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[Any] | A list of document ids.
            collection_name: str | The name of the collection. Default is None.
            kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids, **kwargs)

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs,
    ) -> List[List[dict]]:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[List[dict]] | The query results. Each query result is a list of dictionaries.
            It should include the following fields:
                - required: "ids", "contents"
                - optional: "embeddings", "metadatas", "distances", etc.

            queries example: ["query1", "query2"]
            query results example: [
                {
                    "ids": ["id1", "id2", ...],
                    "contents": ["content1", "content2", ...],
                    "embeddings": ["embedding1", "embedding2", ...],
                    "metadatas": ["metadata1", "metadata2", ...],
                    "distances": ["distance1", "distance2", ...]
                },
                {
                    "ids": ["id1", "id2", ...],
                    "contents": ["content1", "content2", ...],
                    "embeddings": ["embedding1", "embedding2", ...],
                    "metadatas": ["metadata1", "metadata2", ...],
                    "distances": ["distance1", "distance2", ...]
                }
            ]

        """
        collection = self.get_collection(collection_name)
        if isinstance(queries, str):
            queries = [queries]
        results = collection.query(
            query_texts=queries,
            n_results=n_results,
            **kwargs,
        )
        results["contents"] = results.pop("documents")
        return results

    def get_docs_by_ids(self, ids: List[Any], collection_name: str = None, include=None, **kwargs) -> List[dict]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[Any] | A list of document ids.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"]
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[dict] | The query results.
        """
        collection = self.get_collection(collection_name)
        include = include if include else ["metadatas", "documents"]
        results = collection.get(ids, include=include, **kwargs)
        return results
