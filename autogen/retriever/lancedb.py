from typing import Callable, List
from .base import Retriever
try:
    import lancedb
except ImportError:
    raise ImportError("Please install lancedb: pip install lancedb")

class LanceDB(Retriever):
    pass