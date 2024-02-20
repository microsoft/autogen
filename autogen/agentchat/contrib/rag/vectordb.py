from abc import ABC, abstractmethod
from typing import List, Any, Callable
from .datamodel import Document, Query, QueryResults, GetResults
from .encoder import Encoder


class VectorDB(ABC):
    """
    Abstract class for vector database. A vector database is responsible for storing and retrieving documents.
    """

    def __init__(self, path: str = None, embedding_function: Callable = None, metadata: dict = None, **kwargs) -> None:
        """
        Initialize the vector database.

        Args:
            path: str | The path to the vector database. Default is None.
            embedding_function: Callable | The embedding function used to generate the vector representation
                of the documents. Default is None.
            metadata: dict | The metadata of the vector database. Default is None.
            kwargs: dict | Additional keyword arguments.

        Returns:
            None
        """
        raise NotImplementedError

    @abstractmethod
    def create_collection(self, collection_name: str, overwrite: bool = False, get_or_create: bool = True) -> Any:
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
        raise NotImplementedError

    @abstractmethod
    def get_collection(self, collection_name: str = None) -> Any:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Any | The collection object.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            None
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def update_docs(self, docs: List[Document], collection_name: str = None) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            None
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def retrieve_docs(self, queries: List[Query], collection_name: str = None) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[Query] | A list of queries.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            QueryResults | The query results.
        """
        raise NotImplementedError

    @abstractmethod
    def get_docs_by_ids(self, ids: List[Any], collection_name: str = None) -> GetResults:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[Any] | A list of document ids.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            GetResults | The query results.
        """
        raise NotImplementedError

    def convert_get_results_to_query_results(self, get_result: GetResults) -> QueryResults:
        """
        Convert a GetResults object to a QueryResults object.

        Args:
            get_result: GetResults | The GetResults object.

        Returns:
            QueryResults | The QueryResults object.
        """
        return QueryResults(
            ids=[get_result.ids],
            texts=[get_result.texts] if get_result.texts else None,
            embeddings=[get_result.embeddings] if get_result.embeddings else None,
            metadatas=[get_result.metadatas] if get_result.metadatas else None,
        )


class VectorDBFactory:
    """
    Factory class for creating vector databases.
    """

    PREDEFINED_VECTOR_DB = ["chroma"]

    @staticmethod
    def create_vector_db(db_type: str, path: str = None, encoder: Encoder = None, db_config: dict = None) -> VectorDB:
        """
        Create a vector database.

        Args:
            db_type: str | The type of the vector database.
            path: str | The path to the vector database. Default is None.
            encoder: Encoder | The encoder used to generate the vector representation of the documents. Default is None.
            db_config: dict | The configuration of the vector database. Default is None.

        Returns:
            VectorDB | The vector database.
        """
        if db_config is None:
            db_config = {}
        if db_type.lower() in ["chroma", "chromadb"]:
            from .chromadb import ChromaVectorDB

            return ChromaVectorDB(
                path=path, embedding_function=encoder.embedding_function if encoder else None, **db_config
            )
        else:
            raise ValueError(
                f"Unsupported vector database type: {db_type}. Valid types are {VectorDBFactory.PREDEFINED_VECTOR_DB}."
            )
