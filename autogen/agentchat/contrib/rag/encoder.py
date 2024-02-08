from abc import ABC, abstractmethod
from typing import List, Union, Callable
from .datamodel import Document, Vector, Chunk
from .utils import lazy_import, logger, timer


MsgWarningEmbeddingFunction = (
    "The embedding function is not an instance of EmbeddingFunction. Please make sure the embedding "
    "function accepts a string or a list of strings and returns a list of Vectors."
)
MsgErrorEmbeddingFunction = "The embedding function is not callable."
MsgWarningDependentLibrary = "Please install {} to use {}."


class EmbeddingFunction(ABC):
    """
    Abstract class for embedding function. An embedding function is responsible for embedding text, images, etc. into vectors.

    model_name: str | The name of the model.
    dimensions: int | The dimensions of the vectors.
    """

    model_name: str = None
    dimensions: int = None

    @abstractmethod
    def __call__(self, input: Union[str, List[str]]) -> List[Vector]:
        """
        Embed input into vectors.

        Args:
            input: A list of input. If the input is a string, it will be converted to a list of length 1.

        Returns:
            A list of vectors.
        """
        raise NotImplementedError


class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    """
    An embedding function using sentence-transformers.
    More models can be found at [sbert](https://www.sbert.net/docs/pretrained_models.html).
    """

    def __init__(self, model_name: str = "multi-qa-MiniLM-L6-cos-v1"):
        """
        Initialize the embedding function.

        Args:
            model_name: str | The name of the model. Default is "multi-qa-MiniLM-L6-cos-v1".

        Returns:
            None
        """
        self.model_name = model_name
        self.sentence_transformer = lazy_import("sentence_transformers", "SentenceTransformer")(model_name)
        if not self.sentence_transformer:
            raise ImportError(MsgWarningDependentLibrary.format("sentence_transformers", "SentenceTransformer"))
        self.dimensions = self.sentence_transformer.encode(["hello"]).shape[1]

    def __call__(self, input: Union[str, List[str]]) -> List[Vector]:
        """
        Embed input into vectors.

        Args:
            input: A list of input. If the input is a string, it will be converted to a list of length 1.

        Returns:
            A list of vectors.
        """
        if isinstance(input, str):
            input = [input]
        return self.sentence_transformer.encode(input).tolist()


class EmbeddingFunctionFactory:
    """
    Factory class for embedding function.
    """

    PREDEFINED_EMBEDDING_FUNCTIONS = ["sentence_transformer"]

    @staticmethod
    def create_embedding_function(embedding_function: Union[str, Callable]) -> EmbeddingFunction:
        """
        Create an embedding function.

        Args:
            embedding_function: The embedding function.

        Returns:
            An embedding function.
        """
        if isinstance(embedding_function, Callable):
            return embedding_function
        elif embedding_function in ["sentence_transformer"]:
            return SentenceTransformerEmbeddingFunction()
        else:
            raise ValueError(
                f"{MsgErrorEmbeddingFunction} Nor a predefined one. Valid types are {EmbeddingFunctionFactory.PREDEFINED_EMBEDDING_FUNCTIONS}."
            )


class Encoder:
    """
    An encoder is responsible for encoding text, images, etc. into vectors.
    """

    def __init__(self, embedding_function: EmbeddingFunction = SentenceTransformerEmbeddingFunction()):
        """
        Initialize the encoder.

        Args:
            embedding_function: EmbeddingFunction | The embedding function. Default is SentenceTransformerEmbeddingFunction.

        Returns:
            None
        """
        self._embedding_function = embedding_function
        self._model_name = (
            embedding_function.model_name if hasattr(embedding_function, "model_name") else embedding_function.__name__
        )
        self._dimensions = (
            embedding_function.dimensions
            if hasattr(embedding_function, "dimensions")
            else len(embedding_function(["hello"])[0])
        )
        self._print_embedding_function_warning = True

    @timer
    def encode_chunks(self, chunks: List[Chunk]) -> List[Document]:
        """
        Encode Chunks into Documents.

        Args:
            chunks: List[Chunk] | The chunks to be encoded.

        Returns:
            A list of Document.
        """
        if not isinstance(self._embedding_function, Callable):
            raise ValueError(MsgErrorEmbeddingFunction)
        if self._print_embedding_function_warning and not isinstance(self._embedding_function, EmbeddingFunction):
            logger.warning(MsgWarningEmbeddingFunction, color="yellow")
            self._print_embedding_function_warning = False
        return [
            Document(
                **chunk.dict(),
                content_embedding=self._embedding_function(chunk.content)[0] if chunk.content else [],
                embedding_model=self._model_name,
                dimensions=self._dimensions,
            )
            for chunk in chunks
        ]

    @property
    def embedding_function(self) -> EmbeddingFunction:
        """
        Get the embedding function.

        Returns:
            The embedding function.
        """
        return self._embedding_function

    @embedding_function.setter
    def embedding_function(self, new_embedding_function: EmbeddingFunction) -> None:
        """
        Set the embedding function.

        Args:
            new_embedding_function: EmbeddingFunction | The new embedding function.

        Returns:
            None
        """
        if not isinstance(new_embedding_function, EmbeddingFunction):
            logger.warning(MsgWarningEmbeddingFunction, color="yellow")
        if not isinstance(new_embedding_function, Callable):
            raise ValueError(MsgErrorEmbeddingFunction)

        self._embedding_function = new_embedding_function
        self._model_name = (
            new_embedding_function.model_name
            if hasattr(new_embedding_function, "model_name")
            else new_embedding_function.__name__
        )
        self._dimensions = (
            new_embedding_function.dimensions
            if hasattr(new_embedding_function, "dimensions")
            else len(new_embedding_function(["hello"])[0])
        )

    @property
    def model_name(self) -> str:
        """
        Get the model name.

        Returns:
            The model name.
        """
        return self._model_name

    @property
    def dimensions(self) -> int:
        """
        Get the dimensions of the vectors.

        Returns:
            The dimensions of the vectors.
        """
        return self._dimensions
