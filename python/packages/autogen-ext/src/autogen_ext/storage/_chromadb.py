# python\packages\autogen-ext\src\autogen_ext\storage\_chromadb.py

import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Union

from autogen_core.application.logging import TRACE_LOGGER_NAME

if TYPE_CHECKING:
    from chromadb.api import AsyncClientAPI, Client
    from chromadb.api.models.Collection import Collection
    from chromadb.config import Settings

from ._base import AsyncVectorDB, Document, ItemID, QueryResults, VectorDB
from ._utils import chroma_results_to_query_results, filter_results_by_distance

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
        client: Optional["Client"] = None,
        path: Optional[str] = None,
        embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = None,
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
            embedding_function: Callable | The embedding function used to generate the vector representation
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
            import chromadb.utils.embedding_functions as ef
            from chromadb.errors import ChromaError

            ChromaVectorDB.ChromaError = ChromaError  # Set the class attribute
        except ImportError as e:
            raise RuntimeError(
                "Missing dependencies for ChromaVectorDB. Please ensure the autogen-ext package was installed with the 'chromadb' extra."
            ) from e

        self.client: "Client" = client
        self.embedding_function = (
            ef.SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
            if embedding_function is None
            else embedding_function
        )
        self.metadata = metadata if metadata else {}
        self.type = "chroma"
        if not self.client:
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
        docs: List[Document],
        collection_name: Optional[str] = None,
        upsert: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a Pydantic Document model.
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
        if docs[0].id is None:
            raise ValueError("The document id is required.")
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
            metadatas=metadatas,
            documents=documents,
            upsert=upsert,
        )

    def update_docs(self, docs: Sequence[Document], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
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
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids)

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
        results["contents"] = results.pop("documents")
        results = chroma_results_to_query_results(results)
        results = filter_results_by_distance(results, distance_threshold)
        return results

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

    def get_docs_by_ids(
        self,
        ids: Optional[List[ItemID]] = None,
        collection_name: Optional[str] = None,
        include: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: Optional[List[ItemID]] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: Optional[str] | The name of the collection. Default is None.
            include: Optional[List[str]] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"]. IDs are always included.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        collection = self.get_collection(collection_name)
        if include is None:
            include = ["metadatas", "documents"]
        results = collection.get(ids=ids, include=include)
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
        client: "AsyncClientAPI",
        embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = None,
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

            AsyncChromaVectorDB.ChromaError = ChromaError  # Set the class attribute
        except ImportError as e:
            raise RuntimeError(
                "Missing dependencies for AsyncChromaVectorDB. Please ensure the autogen-ext package was installed with the 'chromadb' extra."
            ) from e

        self.client: "AsyncClientAPI" = client
        self.embedding_function = embedding_function
        if self.embedding_function is None:
            raise ValueError("An embedding function must be provided for AsyncChromaVectorDB.")
        self.type = "chroma"
        if not self.client:
            self.client = chromadb.AsyncHttpClient(
                host=host,
                port=port,
                ssl=ssl,
                headers=headers,
                settings=settings,
                tenant=tenant,
                database=database,
                **kwargs,
            )
        self.active_collection: Optional["Collection"] = None

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
        docs: List[Document],
        collection_name: Optional[str] = None,
        upsert: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a Pydantic Document model.
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
        if docs[0].id is None:
            raise ValueError("The document id is required.")
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

    async def update_docs(self, docs: List[Document], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: Optional[str] | The name of the collection. Default is None.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            None
        """
        await self.insert_docs(docs, collection_name=collection_name, upsert=True, **kwargs)

    async def delete_docs(self, ids: List[ItemID], collection_name: Optional[str] = None, **kwargs: Any) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
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
        results["contents"] = results.pop("documents")
        results = chroma_results_to_query_results(results)
        results = filter_results_by_distance(results, distance_threshold)
        return results

    @staticmethod
    def _chroma_get_results_to_list_documents(data_dict: Dict[str, Any]) -> List[Document]:
        """Converts a dictionary with list values to a list of Document.

        Args:
            data_dict: A dictionary where keys map to lists or None.

        Returns:
            List[Document] | The list of Document.
        """
        results = []
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
        ids: Optional[List[ItemID]] = None,
        collection_name: Optional[str] = None,
        include: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: Optional[List[ItemID]] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: Optional[str] | The name of the collection. Default is None.
            include: Optional[List[str]] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"]. IDs are always included.
            kwargs: Dict[str, Any] | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        collection = await self.get_collection(collection_name)
        if include is None:
            include = ["metadatas", "documents"]
        results = await collection.get(ids=ids, include=include)
        results = self._chroma_get_results_to_list_documents(results)
        return results
