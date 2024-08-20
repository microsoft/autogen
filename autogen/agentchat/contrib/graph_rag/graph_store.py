from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GraphStoreQueryResult:
    """
    A wrapper of graph store query results.
    """

    answer: str


class GraphStore(ABC):
    """An abstract base class that represents a underlying graph database.

    This interface defines the basic methods which are required by implementing graph rag from graph database.
    """

    @abstractmethod
    def query(self, question: str, **kwargs) -> GraphStoreQueryResult:
        """
        This method transform a string format question into database query and return the result.
        """
        pass
