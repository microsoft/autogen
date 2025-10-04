from collections.abc import Callable
from typing import Any, Optional

from embedchain.config.embedder.base import BaseEmbedderConfig

try:
    from chromadb.api.types import Embeddable, EmbeddingFunction, Embeddings
except RuntimeError:
    from embedchain.utils.misc import use_pysqlite3

    use_pysqlite3()
    from chromadb.api.types import Embeddable, EmbeddingFunction, Embeddings


class EmbeddingFunc(EmbeddingFunction):
    def __init__(self, embedding_fn: Callable[[list[str]], list[str]]):
        self.embedding_fn = embedding_fn

    def __call__(self, input: Embeddable) -> Embeddings:
        return self.embedding_fn(input)


class BaseEmbedder:
    """
    Class that manages everything regarding embeddings. Including embedding function, loaders and chunkers.

    Embedding functions and vector dimensions are set based on the child class you choose.
    To manually overwrite you can use this classes `set_...` methods.
    """

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        """
        Initialize the embedder class.

        :param config: embedder configuration option class, defaults to None
        :type config: Optional[BaseEmbedderConfig], optional
        """
        if config is None:
            self.config = BaseEmbedderConfig()
        else:
            self.config = config
        self.vector_dimension: int

    def set_embedding_fn(self, embedding_fn: Callable[[list[str]], list[str]]):
        """
        Set or overwrite the embedding function to be used by the database to store and retrieve documents.

        :param embedding_fn: Function to be used to generate embeddings.
        :type embedding_fn: Callable[[list[str]], list[str]]
        :raises ValueError: Embedding function is not callable.
        """
        if not hasattr(embedding_fn, "__call__"):
            raise ValueError("Embedding function is not a function")
        self.embedding_fn = embedding_fn

    def set_vector_dimension(self, vector_dimension: int):
        """
        Set or overwrite the vector dimension size

        :param vector_dimension: vector dimension size
        :type vector_dimension: int
        """
        if not isinstance(vector_dimension, int):
            raise TypeError("vector dimension must be int")
        self.vector_dimension = vector_dimension

    @staticmethod
    def _langchain_default_concept(embeddings: Any):
        """
        Langchains default function layout for embeddings.

        :param embeddings: Langchain embeddings
        :type embeddings: Any
        :return: embedding function
        :rtype: Callable
        """

        return EmbeddingFunc(embeddings.embed_documents)

    def to_embeddings(self, data: str, **_):
        """
        Convert data to embeddings

        :param data: data to convert to embeddings
        :type data: str
        :return: embeddings
        :rtype: list[float]
        """
        embeddings = self.embedding_fn([data])
        return embeddings[0]
