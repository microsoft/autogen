from typing import Callable, List
from collections import defaultdict
from .base import Retriever
try:
    import lancedb
    from lancedb.embeddings import get_registry, EmbeddingFunction, with_embeddings
    from lancedb.pydantic import LanceModel, Vector
    import pyarrow as pa
except ImportError:
    raise ImportError("Please install lancedb: pip install lancedb")

from typing import List
from .base import Retriever
from autogen.retriever.retrieve_utils import (
        split_text_to_chunks,
        extract_text_from_pdf,
        split_files_to_chunks,
        get_files_from_dir
)


class LanceDB(Retriever):
    db = None
    def init_db(self):
        if self.db is None:
            self.db = lancedb.connect(self.path)
        self.embedding_function = (
            get_registry().get("sentence-transformers").create(name=self.embedding_model_name)
            if self.embedding_function is None
            else self.embedding_function
        )
        if self.use_existing and self.name in self.db.table_names():
            self.table = self.db.open_table(self.name)
        else:
            schema = self._get_schema(self.embedding_function)
            self.table = self.db.create_table(self.name, schema=schema)
    
    def ingest_data(self, data_dir):
        """
        Create a vector database from a directory of files.
        Args:
            data_dir: path to the directory containing the text files
        """
        if self.client is None:
            self.init_db()
        if self.custom_text_split_function is not None:
            chunks = split_files_to_chunks(
                get_files_from_dir(data_dir), custom_text_split_function=self.custom_text_split_function
            )
        else:
            chunks = split_files_to_chunks(
                get_files_from_dir(data_dir), self.max_tokens, self.chunk_mode, self.must_break_at_empty_line
            )
        print(f"Found {len(chunks)} chunks.") # 
        data = [ {"documents": docs, "ids": idx } for idx, docs in enumerate(chunks) ]
        if isinstance(self.embedding_function, EmbeddingFunction): # this means we are using embedding API
            self.table.add(data)
        elif isinstance(self.embedding_function, Callable):
            pa_table = pa.Table.from_pylist(data)
            data = with_embeddings(self.embedding_function, pa_table)
            self.table.add(data)


    def query(self, texts: List[str], top_k: int = 10, filter: str = None):
        if self.client is None:
            self.init_db()
        texts = [texts] if isinstance(texts, str) else texts
        results = defaultdict(list)
        for text in texts:
            query = self.embedding_function(text) if isinstance(self.embedding_function, Callable) else text
            print("query: ", query)
            result = self.table.search(query).where(f"documents LIKE '%{filter}%'").limit(top_k).to_arrow().to_pydict()
            for k, v in result.items():
                results[k].append(v)
    
        return results

    def _get_schema(self, embedding_function):
        if isinstance(embedding_function, EmbeddingFunction):
            class Schema(LanceModel):
                vector: Vector(embedding_function.ndims()) = embedding_function.VectorField()
                documents: str = embedding_function.SourceField()
                ids: str

            return Schema
        elif isinstance(embedding_function, Callable):
            dim = embedding_function("test").shape[0] # TODO: check this
            schema = pa.schema(
                [
                    pa.field("Vector", pa.list_(pa.float32(), dim)),
                    pa.field("documents", pa.string()),
                    pa.field("ids", pa.string()),
                ]
            )
            return schema
        else:
            raise ValueError(
                "embedding_function should be a callable or an EmbeddingFunction instance"
            )
    

