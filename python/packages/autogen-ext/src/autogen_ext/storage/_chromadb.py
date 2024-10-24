import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, cast

from autogen_core.application.logging import TRACE_LOGGER_NAME
from chromadb import GetResult, QueryResult

if TYPE_CHECKING:
    from chromadb.api import AsyncClientAPI, ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import Embeddable, EmbeddingFunction, IncludeEnum
    from chromadb.config import Settings

from ._base import AsyncVectorDB, Document, ItemID, QueryResults, VectorDB

CHROMADB_MAX_BATCH_SIZE = int(os.environ.get("CHROMADB_MAX_BATCH_SIZE", 40000))
logger = logging.getLogger(f"{TRACE_LOGGER_NAME}.{__name__}")


class ChromaVectorDB(VectorDB):
    """
    A vector database that uses ChromaDB as the backend.

    .. note::

        This class requires the :code:`chromadb` extra for the :code:`autogen-ext` package.
    """

    ChromaError = Exception  # Default to Exception if chromadb is not installed

    def __init__(
        self,
        *,
        client: Optional["ClientAPI"] = None,
        path: Optional[str] = None,
        embedding_function: Optional[
            Union[Callable[[List[str]], List[List[float]]], "EmbeddingFunction[Embeddable]"]
        ] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client_type: str = "persistent",
        host: str = "localhost",
        port: int = 8000,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the vector database.

        Args:
            client: chromadb.Client | The client object of the vector database. Default is None.
                If provided, it will use the client object directly and ignore other arguments.
            path: Optional[str] | The path to the vector database. Required if client_type is 'persistent'.
            embedding_function: Optional[Union[Callable, EmbeddingFunction]] | The embedding function used to generate the vector representation
                of the documents. Default is None, SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2") will be used.
            metadata: dict | The metadata of the vector database. Default is None.
            client_type: str | The type of client to use. Can be 'persistent' or 'http'. Default is 'persistent'.
            host: str | The host of the HTTP server. Default is 'localhost'.
            port: int | The port of the HTTP server. Default is 8000.
            kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        try:
            import chromadb

            if chromadb.__version__ < "0.5.0":
                raise ImportError("Please upgrade chromadb to version 0.5.0 or later.")
            from chromadb.errors import ChromaError
            from chromadb.utils.embedding_functions.sentence_transformer_embedding_function import (
                SentenceTransformerEmbeddingFunction,
            )

            ChromaVectorDB.ChromaError = ChromaError  # Set the class attribute
        except ImportError as e:
            raise RuntimeError(
                "Missing dependencies for ChromaVectorDB. Please ensure the autogen-ext package was installed with the 'chromadb' extra."
            ) from e

        self.embedding_function: "EmbeddingFunction[Embeddable]" = (  # type: ignore
            SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
            if embedding_function is None
            else cast("EmbeddingFunction[Embeddable]", embedding_function)
        )
        self.metadata = metadata if metadata else {}
        self.type = "chroma"
        if client is not None:
            self.client: "ClientAPI" = client
        else:
            if client_type == "persistent":
                if path is None:
                    raise ValueError("Persistent client requires a 'path' to save the database.")
                self.client = chromadb.PersistentClient(path=path, **kwargs)
            elif client_type == "http":
                self.client = chromadb.HttpClient(host=host, port=port, **kwargs)
            else:
                raise ValueError(f"Invalid client_type: {client_type}")

        self.active_collection: Optional["Collection"] = None

    def create_collection(
        self, collection_name: str, overwrite: bool = False, get_or_create: bool = True
    ) -> "Collection":
        """
        Create a collection in the vector database.
        Case 1. if the collection does not exist, create the collection.
        Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
        Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
            otherwise it raises a ValueError.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True.

        Returns:
            Collection | The collection object.
        """
        try:
            if self.active_collection and self.active_collection.name == collection_name:
                collection = self.active_collection
            else:
                collection = self.client.get_collection(
                    name=collection_name, embedding_function=self.embedding_function
                )
        except (ValueError, ChromaVectorDB.ChromaError):
            collection = None
        if collection is None:
            return self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata=self.metadata,
            )
        elif overwrite:
            self.client.delete_collection(name=collection_name)
            return self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata=self.metadata,
            )
        elif get_or_create:
            return collection
        else:
            raise ValueError(f"Collection {collection_name} already exists.")

    def get_collection(self, collection_name: Optional[str] = None) -> "Collection":
        """
        Get the collection from the vector database.

        Args:
            collection_name: Optional[str] | The name of the collection. Default is None.
                If None, return the current active collection.

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
            if not (self.active_collection and self.active_collection.name == collection_name):
                self.active_collection = self.client.get_collection(
                    name=collection_name, embedding_function=self.embedding_function
                )
        return self.active_collection

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            None
        """
        self.client.delete_collection(name=collection_name)
        if self.active_collection and self.active_collection.name == collection_name:
            self.active_collection = None

    def _batch_insert(
        self,
        collection: "Collection",
        embeddings: Optional[List[Any]] = None,
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        upsert: bool = False,
    ) -> None:
        batch_size = CHROMADB_MAX_BATCH_SIZE
        for i in range(0, len(ids or []), batch_size):
            end_idx = i + batch_size
            collection_kwargs = {
                "documents": documents[i:end_idx] if documents else None,
                "ids": ids[i:end_idx] if ids else None,
                "metadatas": metadatas[i:end_idx] if metadatas else None,
                "embeddings": embeddings[i:end_idx] if embeddings else None,
            }
            if upsert:
                collection.upsert(**collection_kwargs)  # type: ignore
            else:
                collection.add(**collection_kwargs)  # type: ignore

    def insert_docs(
        self,
        docs: Sequence[Document],
        collection_name: Optional[str] = None,
        upsert: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: Sequence[Document] | A list of documents. Each document is a Pydantic Document model.
            collection_name: Optional[str] | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        if not docs:
            return
        if docs[0].content is None and docs[0].embedding is None:
            raise ValueError("Either document content or embedding is required.")
        documents = [doc.content for doc in docs] if docs[0].content else None
        ids = [str(doc.id) for doc in docs]
        collection = self.get_collection(collection_name)
        embeddings = [doc.embedding for doc in docs] if docs[0].embedding else None
        if not embeddings and not documents:
            raise ValueError("Either documents or embeddings must be provided.")
        metadatas = [doc.metadata for doc in docs] if docs[0].metadata else None
        self._batch_insert(
            collection,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,  # type: ignore
            documents=documents,  # type: ignore
            upsert=upsert,
        )

    def update_docs(self, docs: Sequence[Document], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: Sequence[Document] | A list of documents.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        self.insert_docs(docs, collection_name=collection_name, upsert=True, **kwargs)

    def delete_docs(self, ids: Sequence[ItemID], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: Sequence[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=[str(id_) for id_ in ids] if ids else None)

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: Optional[str] = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs: Any,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: Optional[str] | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        collection = self.get_collection(collection_name)
        if isinstance(queries, str):
            queries = [queries]
        results = collection.query(
            query_texts=queries,
            n_results=n_results,
        )
        results_list = _chroma_results_to_query_results(results)
        results_filtered = filter_results_by_distance(results_list, distance_threshold)
        return results_filtered

    @staticmethod
    def _chroma_get_results_to_list_documents(data_dict: GetResult) -> List[Document]:
        """Converts a GetResult dictionary to a list of Document objects.

        Args:
            data_dict: GetResult | A GetResult dictionary containing ids, embeddings, documents, metadatas etc.

        Returns:
            List[Document] | The list of Document objects.
        """
        results: List[Document] = []

        # Get the length from ids which is always present in GetResult
        n_docs = len(data_dict["ids"])

        for i in range(n_docs):
            doc_dict = {}

            # Process each possible field from GetResult
            if data_dict["ids"]:
                doc_dict["id"] = data_dict["ids"][i]
            if data_dict["embeddings"] is not None:
                doc_dict["embedding"] = data_dict["embeddings"][i]
            if data_dict["documents"] is not None:
                doc_dict["document"] = data_dict["documents"][i]
            if data_dict["metadatas"] is not None:
                doc_dict["metadata"] = data_dict["metadatas"][i]
            if data_dict["uris"] is not None:
                doc_dict["uri"] = data_dict["uris"][i]
            if data_dict["data"] is not None:
                doc_dict["data"] = data_dict["data"][i]

            results.append(Document(**doc_dict))  # type: ignore

        return results

    def get_docs_by_ids(
        self,
        ids: Optional[Sequence[ItemID]] = None,
        collection_name: Optional[str] = None,
        include: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: Optional[Sequence[ItemID]] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: Optional[str] | The name of the collection. Default is None.
            include: Optional[List[IncludeEnum]] | The fields to include. Default is None.
                If None, will include [IncludeEnum.metadatas, IncludeEnum.documents]. IDs are always included.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        if include is not None:
            include_enums = [IncludeEnum(item) for item in include]
        else:
            include_enums = [IncludeEnum.metadatas, IncludeEnum.documents]
        collection = self.get_collection(collection_name)

        results = collection.get(ids=[str(id_) for id_ in ids] if ids else None, include=include_enums)
        results = self._chroma_get_results_to_list_documents(results)
        return results


class AsyncChromaVectorDB(AsyncVectorDB):
    """
    An asynchronous vector database that uses ChromaDB as the backend.

    .. note::

        This class requires the :code:`chromadb` extra for the :code:`autogen-ext` package.
    """

    ChromaError = Exception  # Default to Exception if chromadb is not installed

    def __init__(
        self,
        *,
        client: Optional["AsyncClientAPI"] = None,
        embedding_function: Optional[
            Union[Callable[[List[str]], List[List[float]]], "EmbeddingFunction[Embeddable]"]
        ] = None,
        host: str = "localhost",
        port: int = 8000,
        ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
        settings: Optional["Settings"] = None,
        tenant: str = "default_tenant",
        database: str = "default_database",
        **kwargs: Any,
    ) -> None:
        """
        Initialize the async vector database.

        Args:
            client: chromadb.AsyncClientAPI | The client object of the vector database. Default is None.
                If provided, it will use the client object directly and ignore other arguments.
            embedding_function: Callable | The embedding function used to generate the vector representation
                of the documents. Default is None. Must be provided for async client.
            host: str | The host of the HTTP server. Default is 'localhost'.
            port: int | The port of the HTTP server. Default is 8000.
            ssl: bool | Whether to use SSL to connect to the Chroma server. Defaults to False.
            headers: Optional[Dict[str, str]] | A dictionary of headers to send to the Chroma server. Defaults to None.
            settings: Optional[Settings] | A dictionary of settings to communicate with the chroma server.
            tenant: str | The tenant to use for this client. Defaults to "default_tenant".
            database: str | The database to use for this client. Defaults to "default_database".
            kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        try:
            import chromadb

            if chromadb.__version__ < "0.5.0":
                raise ImportError("Please upgrade chromadb to version 0.5.0 or later.")
            from chromadb.errors import ChromaError
            from chromadb.utils.embedding_functions.sentence_transformer_embedding_function import (
                SentenceTransformerEmbeddingFunction,
            )

            AsyncChromaVectorDB.ChromaError = ChromaError  # Set the class attribute
        except ImportError as e:
            raise RuntimeError(
                "Missing dependencies for AsyncChromaVectorDB. Please ensure the autogen-ext package was installed with the 'chromadb' extra."
            ) from e

        self.embedding_function: "EmbeddingFunction[Embeddable]" = (  # type: ignore
            cast(
                "EmbeddingFunction[Embeddable]",
                embedding_function or SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2"),
            )
        )
        self.type = "chroma"
        if client is not None:
            self.client: "AsyncClientAPI" = client
        else:
            self.client = chromadb.AsyncHttpClient(  # type: ignore
                host=host,
                port=port,
                ssl=ssl,
                headers=headers,
                settings=settings,
                tenant=tenant,
                database=database,
                **kwargs,
            )
        self.active_collection: Optional[Any] = None

    async def create_collection(self, collection_name: str, overwrite: bool = False, get_or_create: bool = True) -> Any:
        """
        Create a collection in the vector database.
        Case 1. if the collection does not exist, create the collection.
        Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
        Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
            otherwise it raises a ValueError.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True.

        Returns:
            Any | The collection object.
        """
        try:
            if self.active_collection and self.active_collection.name == collection_name:
                collection = self.active_collection
            else:
                collection = await self.client.get_collection(
                    name=collection_name, embedding_function=self.embedding_function
                )
        except (ValueError, AsyncChromaVectorDB.ChromaError):
            collection = None
        if collection is None:
            return await self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={},
            )
        elif overwrite:
            await self.client.delete_collection(name=collection_name)
            return await self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={},
            )
        elif get_or_create:
            return collection
        else:
            raise ValueError(f"Collection {collection_name} already exists.")

    async def get_collection(self, collection_name: Optional[str] = None) -> Any:
        """
        Get the collection from the vector database.

        Args:
            collection_name: Optional[str] | The name of the collection. Default is None.
                If None, return the current active collection.

        Returns:
            Any | The collection object.
        """
        if collection_name is None:
            if self.active_collection is None:
                raise ValueError("No collection is specified.")
            else:
                logger.info(
                    f"No collection is specified. Using current active collection {self.active_collection.name}."
                )
        else:
            if not (self.active_collection and self.active_collection.name == collection_name):
                self.active_collection = await self.client.get_collection(
                    name=collection_name, embedding_function=self.embedding_function
                )
        return self.active_collection

    async def delete_collection(self, collection_name: str) -> Any:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            Any
        """
        await self.client.delete_collection(name=collection_name)
        if self.active_collection and self.active_collection.name == collection_name:
            self.active_collection = None

    async def _batch_insert(
        self,
        collection: Any,
        embeddings: Optional[List[Any]] = None,
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        upsert: bool = False,
    ) -> None:
        batch_size = CHROMADB_MAX_BATCH_SIZE
        for i in range(0, len(ids or []), batch_size):
            end_idx = i + batch_size
            collection_kwargs = {
                "documents": documents[i:end_idx] if documents else None,
                "ids": ids[i:end_idx] if ids else None,
                "metadatas": metadatas[i:end_idx] if metadatas else None,
                "embeddings": embeddings[i:end_idx] if embeddings else None,
            }
            if upsert:
                await collection.upsert(**collection_kwargs)
            else:
                await collection.add(**collection_kwargs)

    async def insert_docs(
        self,
        docs: Sequence[Document],
        collection_name: Optional[str] = None,
        upsert: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: Sequence[Document] | A list of documents. Each document is a Pydantic Document model.
            collection_name: Optional[str] | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        if not docs:
            return
        if docs[0].content is None and docs[0].embedding is None:
            raise ValueError("Either document content or embedding is required.")
        documents = [doc.content for doc in docs] if docs[0].content else None
        ids = [str(doc.id) for doc in docs]
        collection = await self.get_collection(collection_name)
        embeddings = [doc.embedding for doc in docs] if docs[0].embedding else None
        if not embeddings and not documents:
            raise ValueError("Either documents or embeddings must be provided.")
        metadatas = [doc.metadata for doc in docs] if docs[0].metadata else None
        await self._batch_insert(
            collection,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
            documents=documents,
            upsert=upsert,
        )

    async def update_docs(self, docs: Sequence[Document], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: Sequence[Document] | A list of documents.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        await self.insert_docs(docs, collection_name=collection_name, upsert=True, **kwargs)

    async def delete_docs(self, ids: Sequence[ItemID], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: Sequence[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        collection = await self.get_collection(collection_name)
        await collection.delete(ids=ids)

    async def retrieve_docs(
        self,
        queries: List[str],
        collection_name: Optional[str] = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs: Any,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: Optional[str] | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        collection = await self.get_collection(collection_name)
        if isinstance(queries, str):
            queries = [queries]
        results = await collection.query(
            query_texts=queries,
            n_results=n_results,
        )
        results_list = _chroma_results_to_query_results(results)
        results_filtered = filter_results_by_distance(results_list, distance_threshold)
        return results_filtered

    @staticmethod
    def _chroma_get_results_to_list_documents(data_dict: Dict[str, Any]) -> List[Document]:
        """Converts a dictionary with list values to a list of Document.

        Args:
            data_dict: A dictionary where keys map to lists or None.

        Returns:
            List[Document] | The list of Document.
        """
        results: List[Document] = []
        keys = [key for key in data_dict if data_dict[key] is not None]

        for i in range(len(data_dict[keys[0]])):
            doc_dict = {}
            for key in data_dict.keys():
                if data_dict[key] is not None and len(data_dict[key]) > i:
                    doc_dict[key[:-1]] = data_dict[key][i]
            results.append(Document(**doc_dict))  # type: ignore
        return results

    async def get_docs_by_ids(
        self,
        ids: Optional[Sequence[ItemID]] = None,
        collection_name: Optional[str] = None,
        include: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: Optional[Sequence[ItemID]] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: Optional[str] | The name of the collection. Default is None.
            include: Optional[Sequence[IncludeEnum]] | The fields to include. Default is None.
                If None, will include [IncludeEnum.metadatas, IncludeEnum.documents]. IDs are always included.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        collection = await self.get_collection(collection_name)
        if include is not None:
            include_enums = [IncludeEnum(item) for item in include]
        else:
            include_enums = None
        results = await collection.get(ids=ids, include=include_enums)
        results = self._chroma_get_results_to_list_documents(results)
        return results


def _chroma_results_to_query_results(
    data_dict: QueryResult, special_key: str = "distances"
) -> List[List[Tuple[Dict[str, Any], float]]]:
    """Converts a dictionary with list-of-list values to a list of tuples.

    Args:
        data_dict: A dictionary where keys map to lists of lists or None.
        special_key: str | The key in the dictionary containing the special values
                     for each tuple.

    Returns:
        List[List[Tuple[Dict[str, Any], float]]] | A list of tuples, where each tuple contains
        a sub-dictionary with some keys from the original dictionary and the value from the
        special_key.

    Example:
        data_dict = {
            "key1s": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "key2s": [["a", "b", "c"], ["c", "d", "e"], ["e", "f", "g"]],
            "key3s": None,
            "key4s": [["x", "y", "z"], ["1", "2", "3"], ["4", "5", "6"]],
            "distances": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
        }

        results = [
            [
                ({"key1": 1, "key2": "a", "key4": "x"}, 0.1),
                ({"key1": 2, "key2": "b", "key4": "y"}, 0.2),
                ({"key1": 3, "key2": "c", "key4": "z"}, 0.3),
            ],
            [
                ({"key1": 4, "key2": "c", "key4": "1"}, 0.4),
                ({"key1": 5, "key2": "d", "key4": "2"}, 0.5),
                ({"key1": 6, "key2": "e", "key4": "3"}, 0.6),
            ],
            [
                ({"key1": 7, "key2": "e", "key4": "4"}, 0.7),
                ({"key1": 8, "key2": "f", "key4": "5"}, 0.8),
                ({"key1": 9, "key2": "g", "key4": "6"}, 0.9),
            ],
        ]
    """

    if not data_dict or special_key not in data_dict or not data_dict.get(special_key):
        return []

    result: List[List[Tuple[Document, float]]] = []
    data_special_key: Any = data_dict[special_key]

    if data_special_key is None:
        return result

    for i in range(len(data_special_key)):
        sub_result: List[Tuple[Document, float]] = []
        for j, distance in enumerate(data_special_key[i]):  # type: ignore
            document = data_dict["documents"][i][j]  # type: ignore
            sub_result.append((document, distance))
        result.append(sub_result)

    return result


def filter_results_by_distance(
    results: List[List[Tuple[Dict[str, Any], float]]], distance_threshold: float = -1
) -> QueryResults:
    """Filters results based on a distance threshold.

    Args:
        results: QueryResults | The query results. List[List[Tuple[Document, float]]]
        distance_threshold: The maximum distance allowed for results.

    Returns:
        QueryResults | A filtered results containing only distances smaller than the threshold.
    """

    if distance_threshold > 0:
        results = [[(key, value) for key, value in data if value < distance_threshold] for data in results]

    return results
