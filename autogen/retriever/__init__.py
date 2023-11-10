from .chromadb import ChromaDB
from .lancedb import LanceDB

def get_retriever(type:str):
    if type == "chromadb":
        return ChromaDB
    elif type == "lancedb":
        return LanceDB
    else:
        raise ValueError(f"Unknown retriever type {type}")