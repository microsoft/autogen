from typing import List
from .base import Retriever
from .retrieve_utils import split_text_to_chunks, extract_text_from_pdf, split_files_to_chunks, get_files_from_dir

try:
    import chromadb

    if chromadb.__version__ < "0.4.15":
        from chromadb.api import API
    else:
        from chromadb.api import ClientAPI as API
    from chromadb.api.types import QueryResult
    import chromadb.utils.embedding_functions as ef
except ImportError:
    raise ImportError("Please install chromadb: pip install chromadb")


class ChromaDB(Retriever):
    def init_db(self):
        if self.client is None:
            self.client = chromadb.PersistentClient(path=self.path)
        embedding_function = (
            ef.SentenceTransformerEmbeddingFunction(self.embedding_model_name)
            if self.embedding_function is None
            else embedding_function
        )
        self.collection = self.client.create_collection(
            self.name,
            get_or_create=self.use_existing,
            embedding_function=embedding_function,
            # https://github.com/nmslib/hnswlib#supported-distances
            # https://github.com/chroma-core/chroma/blob/566bc80f6c8ee29f7d99b6322654f32183c368c4/chromadb/segment/impl/vector/local_hnsw.py#L184
            # https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
            metadata={"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32},  # ip, l2, cosine
        )

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
        print(f"Found {len(chunks)} chunks.")  #
        # Upsert in batch of 40000 or less if the total number of chunks is less than 40000
        for i in range(0, len(chunks), min(40000, len(chunks))):
            end_idx = i + min(40000, len(chunks) - i)
            self.collection.upsert(
                documents=chunks[i:end_idx],
                ids=[f"doc_{j}" for j in range(i, end_idx)],  # unique for each doc
            )

    def query(self, texts: List[str], top_k: int = 10, filter: str = None):
        if self.client is None:
            self.init_db()
        # the collection's embedding function is always the default one, but we want to use the one we used to create the
        # collection. So we compute the embeddings ourselves and pass it to the query function.
        embedding_function = (
            ef.SentenceTransformerEmbeddingFunction(self.embedding_model_name)
            if self.embedding_function is None
            else self.embedding_function
        )
        query_embeddings = embedding_function(texts)
        # Query/search n most similar results. You can also .get by id
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
            where_document={"$contains": filter} if filter else None,  # optional filter
        )
        return results
