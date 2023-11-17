from abc import ABC, abstractmethod
from typing import List, Union, Callable, Any


class Retriever(ABC):
    def __init__(
        self,
        path="./db",
        name="vectorstore",
        embedding_model_name="all-MiniLM-L6-v2",
        embedding_function=None,
        max_tokens: int = 4000,
        chunk_mode: str = "multi_lines",
        must_break_at_empty_line: bool = True,
        custom_text_split_function: Callable = None,
        use_existing=False,
        client=None,
    ):
        """
        Args:
            path: path to the folder where the database is stored
            name: name of the database
            embedding_model_name: name of the embedding model to use
            embedding_function: function to use to embed the text
            max_tokens: maximum number of tokens to embed
            chunk_mode: mode to chunk the text. Can be "multi_lines" or "single_line"
            must_break_at_empty_line: whether to break the text at empty lines when chunking
            custom_text_split_function: custom function to split the text into chunks
        """
        self.path = path
        self.name = name
        self.embedding_model_name = embedding_model_name
        self.embedding_function = embedding_function
        self.max_tokens = max_tokens
        self.chunk_mode = chunk_mode
        self.must_break_at_empty_line = must_break_at_empty_line
        self.custom_text_split_function = custom_text_split_function
        self.use_existing = use_existing
        self.client = client

        self.init_db()

    @abstractmethod
    def ingest_data(self, data_dir):
        """
        Create a vector database from a directory of files.
        Args:
            data_dir: path to the directory containing the text files
        """
        pass

    @abstractmethod
    def query(self, texts: List[str], top_k: int = 10, filter: Any = None):
        """
        Query the database.
        Args:
            query: query string or list of query strings
            top_k: number of results to return
        """
        pass

    @abstractmethod
    def init_db(self):
        """
        Initialize the database.
        """
        pass
