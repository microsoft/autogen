from typing import List, Any, Callable
from .datamodel import Document, Query, QueryResults, GetResults
from .vectordb import VectorDB
from .utils import logger, timer
from .constants import CHROMADB_MAX_BATCH_SIZE

try:
    import chromadb

    if chromadb.__version__ < "0.4.15":
        raise ImportError("Please upgrade chromadb to version 0.4.15 or later.")
    from chromadb.api.models.Collection import Collection
except ImportError:
    raise ImportError("Please install chromadb: `pip install chromadb`")


class ChromaVectorDB(VectorDB):
    """
    A vector database that uses ChromaDB as the backend.
    """

    def __init__(self, path: str = None, embedding_function: Callable = None, metadata: dict = None, **kwargs):
        """
        Initialize the vector database.

        Args:
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
        self.path = path
        self.embedding_function = embedding_function
        self.metadata = metadata if metadata else {"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32}
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

    @timer
    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.

        Returns:
            None
        """
        if not docs:
            return
        collection = self.get_collection(collection_name)
        if docs[0].content_embedding is None:
            logger.info(
                "No content embedding is provided. Will use the VectorDB's embedding function to generate the content embedding."
            )
            embeddings = None
        else:
            embeddings = [doc.content_embedding for doc in docs]
        documents = [doc.content for doc in docs]
        ids = [doc.id for doc in docs]
        metadata = [doc.metadata for doc in docs]
        self._batch_insert(collection, embeddings, ids, metadata, documents, upsert)

    def update_docs(self, docs: List[Document], collection_name: str = None) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
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

    def retrieve_docs(self, queries: List[Query], collection_name: str = None) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[Query] | A list of queries.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            QueryResults | The query results.
        """
        collection = self.get_collection(collection_name)
        results = collection.query(
            query_texts=[q.text for q in queries],
            n_results=queries[0].k,
            where=queries[0].filter_metadata,
            where_document=queries[0].filter_document,
            include=queries[0].include if queries[0].include else ["distances", "documents", "metadatas"],
        )
        return QueryResults(
            ids=results.get("ids"),
            texts=results.get("documents"),
            embeddings=results.get("embeddings"),
            metadatas=results.get("metadatas"),
            distances=results.get("distances"),
        )

    def get_docs_by_ids(self, ids: List[Any], collection_name: str = None, include=None, **kwargs) -> GetResults:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[Any] | A list of document ids.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"]
            kwargs: dict | Additional keyword arguments.

        Returns:
            GetResults | The query results.
        """
        collection = self.get_collection(collection_name)
        include = include if include else ["metadatas", "documents"]
        results = collection.get(ids, include=include, **kwargs)
        return GetResults(
            ids=results.get("ids"),
            texts=results.get("documents"),
            embeddings=results.get("embeddings"),
            metadatas=results.get("metadatas"),
        )
