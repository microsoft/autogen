from abc import ABC, abstractmethod
from typing import List, Dict
from .datamodel import Query, QueryResults, ItemID, GetResults
from .encoder import Encoder
from .vectordb import VectorDBFactory
from .utils import timer


class Retriever(ABC):
    """
    Abstract class for retriever. A retriever is responsible for retrieving documents from the vector database.
    """

    def __init__(
        self,
        db_type: str,
        collection_name: str,
        path: str,
        encoder: Encoder = None,
        db_config: Dict = None,
    ) -> None:
        """
        Initialize the retriever.

        Args:
            db_type: str | The type of the vector database.
            collection_name: str | The name of the collection.
            path: str | The path to the vector database.
            encoder: Encoder | The encoder used to encode the documents. Default is None.
            db_config: Dict | The configuration of the vector database. Default is None.

        Returns:
            None
        """
        self.db_type = db_type
        self.collection_name = collection_name
        self.path = path
        self.encoder = encoder
        self.db_config = db_config
        self.vector_db = VectorDBFactory.create_vector_db(
            db_type=db_type, path=path, encoder=encoder, db_config=db_config
        )

    @timer
    def retrieve_docs(self, queries: List[Query]) -> QueryResults:
        """
        Retrieve documents from the vector database based on the queries.

        Args:
            queries: List[Query] | A list of queries.

        Returns:
            QueryResults | The query results.
        """
        return self.vector_db.retrieve_docs(queries=queries, collection_name=self.collection_name)

    @timer
    def get_docs_by_ids(self, ids: List[ItemID]) -> GetResults:
        """
        Retrieve documents from the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids.

        Returns:
            GetResults | The query results.
        """
        return self.vector_db.get_docs_by_ids(ids=ids, collection_name=self.collection_name)

    @timer
    def convert_get_results_to_query_results(self, get_result: GetResults) -> QueryResults:
        """
        Convert a GetResults object to a QueryResults object.

        Args:
            get_result: GetResults | The GetResults object.

        Returns:
            QueryResults | The QueryResults object.
        """
        return self.vector_db.convert_get_results_to_query_results(get_result)


class ChromaRetriever(Retriever):
    """
    A retriever that retrieves documents based on the chroma vector database.
    """

    def __init__(
        self,
        collection_name: str = "default",
        path: str = None,
        encoder: Encoder = None,
        db_config: Dict = None,
    ) -> None:
        """
        Initialize the chroma retriever.

        Args:
            collection_name: str | The name of the collection. Default is "default".
            path: str | The path to the vector database. Default is None. Set to "-1" to use in-memory database.
            encoder: Encoder | The encoder used to encode the documents. Default is None.
            db_config: Dict | The configuration of the vector database. Default is None.

        Returns:
            None
        """
        super().__init__(
            "chroma", collection_name, None if path == "-1" else path if path else "./tmp/chroma", encoder, db_config
        )
        self.name = "chroma"


class RetrieverFactory:
    """
    Factory class for creating retrievers.
    """

    PREDEFINED_RETRIEVERS = frozenset({"chroma"})

    @staticmethod
    def create_retriever(
        retriever_name: str,
        collection_name: str = "default",
        path: str = None,
        encoder: Encoder = None,
        db_config: Dict = None,
    ) -> Retriever:
        """
        Create a retriever.

        Args:
            retriever_name: str | The name of the retriever.
            collection_name: str | The name of the collection. Default is "default".
            path: str | The path to the vector database. Default is None.
            encoder: Encoder | The encoder used to encode the documents. Default is None.
            db_config: Dict | The configuration of the vector database. Default is None.

        Returns:
            Retriever | The retriever.
        """
        if retriever_name.lower() in ["chroma", "chromadb"]:
            return ChromaRetriever(collection_name, path, encoder, db_config)
        else:
            raise ValueError(
                f"Retriever {retriever_name} is not supported. Valid retrievers are {RetrieverFactory.PREDEFINED_RETRIEVERS}."
            )
