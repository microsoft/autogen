from typing import Any, Dict, List, Mapping, Optional, Sequence, TypedDict, Union

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
