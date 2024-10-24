from typing import Any, Literal

from ._base import VectorDB


class VectorDBFactory:
    """
    Factory class for creating vector databases.
    """

    PREDEFINED_VECTOR_DB = ["chromadb"]

    @staticmethod
    def create_vector_db(db_type: Literal["chromadb"], **kwargs: Any) -> VectorDB:
        """
        Create a vector database.

        Args:
            db_type: Literal["chroma", "chromadb"] | The type of the vector database.
            kwargs: Dict | The keyword arguments for initializing the vector database.

        Returns:
            VectorDB | The vector database.
        """
        if db_type.lower() == "chromadb":
            from ._chromadb import ChromaVectorDB

            return ChromaVectorDB(**kwargs)  # type: ignore

        else:
            raise ValueError(
                f"Unsupported vector database type: {db_type}. Valid types are {VectorDBFactory.PREDEFINED_VECTOR_DB}."
            )
