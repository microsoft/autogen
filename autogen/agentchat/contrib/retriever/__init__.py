from typing import Optional
from .chromadb import ChromaDB
from .lancedb import LanceDB

AVILABLE_RETRIEVERS = ["lanchedb", "chromadb"]
DEFAULT_RETRIEVER = "lancedb"


def get_retriever(type: Optional[str] = None):
    """Return a retriever instance."""
    type = type or DEFAULT_RETRIEVER
    if type == "chromadb":
        return ChromaDB
    elif type == "lancedb":
        return LanceDB
    else:
        raise ValueError(f"Unknown retriever type {type}")
