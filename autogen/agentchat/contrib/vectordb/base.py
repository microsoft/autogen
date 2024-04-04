from typing import Any, List, Mapping, Optional, Protocol, Sequence, TypedDict, Union, runtime_checkable

Metadata = Union[Mapping[str, Union[str, int, float, bool, None]], None]
Vector = Union[Sequence[float], Sequence[int]]
ItemID = str  # chromadb doesn't support int ids


class Document(TypedDict):
    """A Document is a record in the vector database.

    id: ItemID | the unique identifier of the document.
    content: str | the text content of the chunk.
    metadata: Metadata | contains additional information about the document such as source, date, etc.
    embedding: Vector | the vector representation of the content.
    dimensions: int | the dimensions of the content_embedding.
    """

    id: ItemID
    content: str
    metadata: Optional[Metadata]
    embedding: Optional[Vector]
    dimensions: Optional[int]


class QueryResults(TypedDict):
    """QueryResults is the response from the vector database for a query.

    ids: List[List[ItemID]] | the unique identifiers of the documents.
    contents: List[List[str]] | the text content of the documents.
    embeddings: List[List[Vector]] | the vector representations of the documents.
    metadatas: List[List[Metadata]] | the metadata of the documents.
    distances: List[List[float]] | the distances between the query and the documents.
    """

    ids: List[List[ItemID]]
    contents: List[List[str]]
    embeddings: Optional[List[List[Vector]]]
    metadatas: Optional[List[List[Metadata]]]
    distances: Optional[List[List[float]]]


class GetResults(TypedDict):
    """GetResults is the response from the vector database for getting documents by ids.

    ids: List[ItemID] | the unique identifiers of the documents.
    contents: List[str] | the text content of the documents.
    embeddings: List[Vector] | the vector representations of the documents.
    metadatas: List[Metadata] | the metadata of the documents.
    """

    ids: List[ItemID]
    contents: Optional[List[str]]
    embeddings: Optional[List[Vector]]
    metadatas: Optional[List[Metadata]]


@runtime_checkable
class VectorDB(Protocol):
    """
    Abstract class for vector database. A vector database is responsible for storing and retrieving documents.
    """

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
        ...

    def get_collection(self, collection_name: str = None) -> Any:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Any | The collection object.
        """
        ...

    def delete_collection(self, collection_name: str) -> Any:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            Any
        """
        ...

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False, **kwargs) -> None:
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
        ...

    def update_docs(self, docs: List[Document], collection_name: str = None, **kwargs) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        ...

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
        ...

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a TypedDict `QueryResults`.
            It should include the following fields:
                - required: "ids", "contents"
                - optional: "embeddings", "metadatas", "distances", etc.

            queries example: ["query1", "query2"]
            query results example: {
                "ids": [["id1", "id2", ...], ["id3", "id4", ...]],
                "contents": [["content1", "content2", ...], ["content3", "content4", ...]],
                "embeddings": [["embedding1", "embedding2", ...], ["embedding3", "embedding4", ...]],
                "metadatas": [["metadata1", "metadata2", ...], ["metadata3", "metadata4", ...]],
                "distances": [["distance1", "distance2", ...], ["distance3", "distance4", ...]],
            }

        """
        ...

    def get_docs_by_ids(self, ids: List[ItemID], collection_name: str = None, include=None, **kwargs) -> GetResults:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[Any] | A list of document ids.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"]. ids are always included.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            GetResults | The results.
        """
        ...


class VectorDBFactory:
    """
    Factory class for creating vector databases.
    """

    PREDEFINED_VECTOR_DB = ["chroma"]

    @staticmethod
    def create_vector_db(db_type: str, **kwargs) -> VectorDB:
        """
        Create a vector database.

        Args:
            db_type: str | The type of the vector database.
            kwargs: Dict | The keyword arguments for initializing the vector database.

        Returns:
            VectorDB | The vector database.
        """
        if db_type.lower() in ["chroma", "chromadb"]:
            from .chromadb import ChromaVectorDB

            return ChromaVectorDB(**kwargs)
        else:
            raise ValueError(
                f"Unsupported vector database type: {db_type}. Valid types are {VectorDBFactory.PREDEFINED_VECTOR_DB}."
            )
