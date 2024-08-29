import abc
import logging
import os
from typing import Callable, List, Optional, Sequence, Tuple, Union

from .base import Document, ItemID, QueryResults, VectorDB
from .utils import get_logger

try:
    from qdrant_client import QdrantClient, models
except ImportError:
    raise ImportError("Please install qdrant-client: `pip install qdrant-client`")

logger = get_logger(__name__)

Embeddings = Union[Sequence[float], Sequence[int]]


class EmbeddingFunction(abc.ABC):
    @abc.abstractmethod
    def __call__(self, inputs: List[str]) -> List[Embeddings]:
        raise NotImplementedError


class FastEmbedEmbeddingFunction(EmbeddingFunction):
    """Embedding function implementation using FastEmbed - https://qdrant.github.io/fastembed."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 256,
        cache_dir: Optional[str] = None,
        threads: Optional[int] = None,
        parallel: Optional[int] = None,
        **kwargs,
    ):
        """Initialize fastembed.TextEmbedding.

        Args:
            model_name (str): The name of the model to use. Defaults to `"BAAI/bge-small-en-v1.5"`.
            batch_size (int): Batch size for encoding. Higher values will use more memory, but be faster.\
                                        Defaults to 256.
            cache_dir (str, optional): The path to the model cache directory.\
                                       Can also be set using the `FASTEMBED_CACHE_PATH` env variable.
            threads (int, optional): The number of threads single onnxruntime session can use.
            parallel (int, optional): If `>1`, data-parallel encoding will be used, recommended for large datasets.\
                                      If `0`, use all available cores.\
                                      If `None`, don't use data-parallel processing, use default onnxruntime threading.\
                                      Defaults to None.
            **kwargs: Additional options to pass to fastembed.TextEmbedding
        Raises:
            ValueError: If the model_name is not in the format <org>/<model> e.g. BAAI/bge-small-en-v1.5.
        """
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise ValueError(
                "The 'fastembed' package is not installed. Please install it with `pip install fastembed`",
            ) from e
        self._batch_size = batch_size
        self._parallel = parallel
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, threads=threads, **kwargs)

    def __call__(self, inputs: List[str]) -> List[Embeddings]:
        embeddings = self._model.embed(inputs, batch_size=self._batch_size, parallel=self._parallel)

        return [embedding.tolist() for embedding in embeddings]


class QdrantVectorDB(VectorDB):
    """
    A vector database implementation that uses Qdrant as the backend.
    """

    def __init__(
        self,
        *,
        client=None,
        embedding_function: EmbeddingFunction = None,
        content_payload_key: str = "_content",
        metadata_payload_key: str = "_metadata",
        collection_options: dict = {},
        **kwargs,
    ) -> None:
        """
        Initialize the vector database.

        Args:
            client: qdrant_client.QdrantClient | An instance of QdrantClient.
            embedding_function: Callable | The embedding function used to generate the vector representation
                of the documents. Defaults to FastEmbedEmbeddingFunction.
            collection_options: dict | The options for creating the collection.
            kwargs: dict | Additional keyword arguments.
        """
        self.client: QdrantClient = client or QdrantClient(location=":memory:")
        self.embedding_function = embedding_function or FastEmbedEmbeddingFunction()
        self.collection_options = collection_options
        self.content_payload_key = content_payload_key
        self.metadata_payload_key = metadata_payload_key
        self.type = "qdrant"

    def create_collection(self, collection_name: str, overwrite: bool = False, get_or_create: bool = True) -> None:
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
            Any | The collection object.
        """
        embeddings_size = len(self.embedding_function(["test"])[0])

        if self.client.collection_exists(collection_name) and overwrite:
            self.client.delete_collection(collection_name)

        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name,
                vectors_config=models.VectorParams(size=embeddings_size, distance=models.Distance.COSINE),
                **self.collection_options,
            )
        elif not get_or_create:
            raise ValueError(f"Collection {collection_name} already exists.")

    def get_collection(self, collection_name: str = None):
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            Any | The collection object.
        """
        if collection_name is None:
            raise ValueError("The collection name is required.")

        return self.client.get_collection(collection_name)

    def delete_collection(self, collection_name: str) -> None:
        """Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            Any
        """
        return self.client.delete_collection(collection_name)

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        if not docs:
            return
        if any(doc.get("content") is None for doc in docs):
            raise ValueError("The document content is required.")
        if any(doc.get("id") is None for doc in docs):
            raise ValueError("The document id is required.")

        if not upsert and not self._validate_upsert_ids(collection_name, [doc["id"] for doc in docs]):
            logger.log("Some IDs already exist. Skipping insert", level=logging.WARN)

        self.client.upsert(collection_name, points=self._documents_to_points(docs))

    def update_docs(self, docs: List[Document], collection_name: str = None) -> None:
        if not docs:
            return
        if any(doc.get("id") is None for doc in docs):
            raise ValueError("The document id is required.")
        if any(doc.get("content") is None for doc in docs):
            raise ValueError("The document content is required.")
        if self._validate_update_ids(collection_name, [doc["id"] for doc in docs]):
            return self.client.upsert(collection_name, points=self._documents_to_points(docs))

        raise ValueError("Some IDs do not exist. Skipping update")

    def delete_docs(self, ids: List[ItemID], collection_name: str = None, **kwargs) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        self.client.delete(collection_name, ids)

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = 0,
        **kwargs,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is 0.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        embeddings = self.embedding_function(queries)
        requests = [
            models.SearchRequest(
                vector=embedding,
                limit=n_results,
                score_threshold=distance_threshold,
                with_payload=True,
                with_vector=False,
            )
            for embedding in embeddings
        ]

        batch_results = self.client.search_batch(collection_name, requests)
        return [self._scored_points_to_documents(results) for results in batch_results]

    def get_docs_by_ids(
        self, ids: List[ItemID] = None, collection_name: str = None, include=True, **kwargs
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is True.
                If None, will include ["metadatas", "documents"], ids will always be included.
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        if ids is None:
            results = self.client.scroll(collection_name=collection_name, with_payload=include, with_vectors=True)[0]
        else:
            results = self.client.retrieve(collection_name, ids=ids, with_payload=include, with_vectors=True)
        return [self._point_to_document(result) for result in results]

    def _point_to_document(self, point) -> Document:
        return {
            "id": point.id,
            "content": point.payload.get(self.content_payload_key, ""),
            "metadata": point.payload.get(self.metadata_payload_key, {}),
            "embedding": point.vector,
        }

    def _points_to_documents(self, points) -> List[Document]:
        return [self._point_to_document(point) for point in points]

    def _scored_point_to_document(self, scored_point: models.ScoredPoint) -> Tuple[Document, float]:
        return self._point_to_document(scored_point), scored_point.score

    def _documents_to_points(self, documents: List[Document]):
        contents = [document["content"] for document in documents]
        embeddings = self.embedding_function(contents)
        points = [
            models.PointStruct(
                id=documents[i]["id"],
                vector=embeddings[i],
                payload={
                    self.content_payload_key: documents[i].get("content"),
                    self.metadata_payload_key: documents[i].get("metadata"),
                },
            )
            for i in range(len(documents))
        ]
        return points

    def _scored_points_to_documents(self, scored_points: List[models.ScoredPoint]) -> List[Tuple[Document, float]]:
        return [self._scored_point_to_document(scored_point) for scored_point in scored_points]

    def _validate_update_ids(self, collection_name: str, ids: List[str]) -> bool:
        """
        Validates all the IDs exist in the collection
        """
        retrieved_ids = [
            point.id for point in self.client.retrieve(collection_name, ids=ids, with_payload=False, with_vectors=False)
        ]

        if missing_ids := set(ids) - set(retrieved_ids):
            logger.log(f"Missing IDs: {missing_ids}. Skipping update", level=logging.WARN)
            return False

        return True

    def _validate_upsert_ids(self, collection_name: str, ids: List[str]) -> bool:
        """
        Validate none of the IDs exist in the collection
        """
        retrieved_ids = [
            point.id for point in self.client.retrieve(collection_name, ids=ids, with_payload=False, with_vectors=False)
        ]

        if existing_ids := set(ids) & set(retrieved_ids):
            logger.log(f"Existing IDs: {existing_ids}.", level=logging.WARN)
            return False

        return True
