from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class GraphStoreQueryResult:
    """
    A wrapper of graph store query results.

    answer: human readable answer to question/query.
    results: intermediate results to question/query, e.g. node entities.
    """

    answer: Optional[str] = None
    results: Optional[List] = []


class GraphStore(Protocol):
    """An abstract base class that represents a underlying graph database.

    This interface defines the basic methods which are required by implementing graph rag from graph database.
    """

    def query(self, question: str, n_results: int = 1, **kwargs) -> GraphStoreQueryResult:
        """
        This method transform a string format question into database query and return the result.
        """
        pass
