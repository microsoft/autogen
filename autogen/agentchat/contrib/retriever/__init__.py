from typing import Optional

AVILABLE_RETRIEVERS = ["lanchedb", "chromadb"]
DEFAULT_RETRIEVER = "lancedb"


def get_retriever(type: Optional[str] = None):
    """Return a retriever instance."""
    type = type or DEFAULT_RETRIEVER
    if type == "chromadb":
        from .chromadb import ChromaDB

        return ChromaDB
    elif type == "lancedb":
        from .lancedb import LanceDB

        return LanceDB
    else:
        raise ValueError(f"Unknown retriever type {type}")
