from typing import Any, Dict, List, Optional, Union, Mapping, Sequence
from pydantic.dataclasses import dataclass
from dataclasses import asdict


Metadata = Mapping[str, Union[str, int, float, bool, None]]
Vector = Union[Sequence[float], Sequence[int]]
ItemID = Union[str, int]


@dataclass
class Chunk(object):
    """A Chunk is a piece of data that is used to generate a document for the vector database.
    The data sources include texts, codes, database metadata, etc. After processed by splitters, the raw data
    are split into chunks. Chunks are then used to generate documents for the vector database.

    content: str | the text content of the chunk.
    id: ItemID | the unique identifier of the chunk. If not provided, it will be the hash value of the content.
    metadata: Metadata | contains additional information about the document such as source, date, etc.
    """

    content: str
    id: ItemID = None
    metadata: Optional[Metadata] = None

    def __post_init__(self):
        if self.id is None:
            self.id = abs(hash(self.content))

    def dict(self):
        result = asdict(self)
        return result


@dataclass
class Document(Chunk):
    """A Document is extended from Chunk. It is a record in the vector database.

    content_embedding: Vector | the vector representation of the content.
    embedding_model: str | the name of the embedding model used to generate the content_embedding.
    dimensions: int | the dimensions of the content_embedding.
    """

    content_embedding: Optional[Vector] = None
    embedding_model: Optional[str] = None
    dimensions: Optional[int] = None


@dataclass
class QueryResults(object):
    """QueryResults is the response from the vector database for a query.

    ids: List[List[ItemID]] | the unique identifiers of the documents.
    texts: List[List[str]] | the text content of the documents.
    embeddings: List[List[Vector]] | the vector representations of the documents.
    metadatas: List[List[Metadata]] | the metadata of the documents.
    distances: List[List[float]] | the distances between the query and the documents.
    """

    ids: List[List[ItemID]]
    texts: Optional[List[List[str]]] = None
    embeddings: Optional[List[List[Vector]]] = None
    metadatas: Optional[List[List[Metadata]]] = None
    distances: Optional[List[List[float]]] = None

    def dict(self):
        result = asdict(self)
        return result


@dataclass
class Query(object):
    """A Query is a request to the vector database for similar documents to the query.

    text: str | the text content of the query.
    k: int | the number of similar documents to return.
    filter_metadata: Dict[str, Any] | int a dictionary that contains additional conditions for the metadata.
    filter_document: Dict[str, Any] | a dictionary that contains additional conditions for the document.
    include: List[str] | a list of fields to include in the response.
    """

    text: str
    k: int = 10  # The number of similar documents to return.
    filter_metadata: Optional[Dict[str, Any]] = None
    filter_document: Optional[Dict[str, Any]] = None
    include: Optional[List[str]] = None

    def dict(self):
        result = asdict(self)
        return result


@dataclass
class GetResults(object):
    """GetResults is the response from the vector database for getting documents by ids.

    ids: List[ItemID] | the unique identifiers of the documents.
    texts: List[str] | the text content of the documents.
    embeddings: List[Vector] | the vector representations of the documents.
    metadatas: List[Metadata] | the metadata of the documents.
    """

    ids: List[ItemID]
    texts: Optional[List[str]] = None
    embeddings: Optional[List[Vector]] = None
    metadatas: Optional[List[Metadata]] = None

    def dict(self):
        result = asdict(self)
        return result
