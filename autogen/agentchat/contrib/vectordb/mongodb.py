from copy import deepcopy
from time import monotonic, sleep
from typing import Any, Callable, Dict, Iterable, List, Literal, Mapping, Set, Tuple, Union

import numpy as np
from pymongo import MongoClient, UpdateOne, errors
from pymongo.collection import Collection
from pymongo.driver_info import DriverInfo
from pymongo.operations import SearchIndexModel
from sentence_transformers import SentenceTransformer

from .base import Document, ItemID, QueryResults, VectorDB
from .utils import get_logger

logger = get_logger(__name__)

DEFAULT_INSERT_BATCH_SIZE = 100_000
_SAMPLE_SENTENCE = ["The weather is lovely today in paradise."]
_DELAY = 0.5


def with_id_rename(docs: Iterable) -> List[Dict[str, Any]]:
    """Utility changes _id field from Collection into id for Document."""
    return [{**{k: v for k, v in d.items() if k != "_id"}, "id": d["_id"]} for d in docs]


class MongoDBAtlasVectorDB(VectorDB):
    """
    A Collection object for MongoDB.
    """

    def __init__(
        self,
        connection_string: str = "",
        database_name: str = "vector_db",
        embedding_function: Callable = SentenceTransformer("all-MiniLM-L6-v2").encode,
        collection_name: str = None,
        index_name: str = "vector_index",
        overwrite: bool = False,
        wait_until_index_ready: float = None,
        wait_until_document_ready: float = None,
    ):
        """
        Initialize the vector database.

        Args:
            connection_string: str | The MongoDB connection string to connect to. Default is ''.
            database_name: str | The name of the database. Default is 'vector_db'.
            embedding_function: Callable | The embedding function used to generate the vector representation.
            collection_name: str | The name of the collection to create for this vector database
                Defaults to None
            index_name: str | Index name for the vector database, defaults to 'vector_index'
            overwrite: bool = False
            wait_until_index_ready: float | None | Blocking call to wait until the
                database indexes are ready. None, the default, means no wait.
            wait_until_document_ready: float | None | Blocking call to wait until the
                database indexes are ready. None, the default, means no wait.
        """
        self.embedding_function = embedding_function
        self.index_name = index_name
        self._wait_until_index_ready = wait_until_index_ready
        self._wait_until_document_ready = wait_until_document_ready

        # This will get the model dimension size by computing the embeddings dimensions
        self.dimensions = self._get_embedding_size()

        try:
            self.client = MongoClient(connection_string, driver=DriverInfo(name="autogen"))
            self.client.admin.command("ping")
            logger.debug("Successfully created MongoClient")
        except errors.ServerSelectionTimeoutError as err:
            raise ConnectionError("Could not connect to MongoDB server") from err

        self.db = self.client[database_name]
        logger.debug(f"Atlas Database name: {self.db.name}")
        if collection_name:
            self.active_collection = self.create_collection(collection_name, overwrite)
        else:
            self.active_collection = None

    def _is_index_ready(self, collection: Collection, index_name: str):
        """Check for the index name in the list of available search indexes to see if the
        specified index is of status READY

        Args:
            collection (Collection): MongoDB Collection to for the search indexes
            index_name (str): Vector Search Index name

        Returns:
            bool : True if the index is present and READY false otherwise
        """
        for index in collection.list_search_indexes(index_name):
            if index["type"] == "vectorSearch" and index["status"] == "READY":
                return True
        return False

    def _wait_for_index(self, collection: Collection, index_name: str, action: str = "create"):
        """Waits for the index action to be completed. Otherwise throws a TimeoutError.

        Timeout set on instantiation.
        action: "create" or "delete"
        """
        assert action in ["create", "delete"], f"{action=} must be create or delete."
        start = monotonic()
        while monotonic() - start < self._wait_until_index_ready:
            if action == "create" and self._is_index_ready(collection, index_name):
                return
            elif action == "delete" and len(list(collection.list_search_indexes())) == 0:
                return
            sleep(_DELAY)

        raise TimeoutError(f"Index {self.index_name} is not ready!")

    def _wait_for_document(self, collection: Collection, index_name: str, doc: Document):
        start = monotonic()
        while monotonic() - start < self._wait_until_document_ready:
            query_result = _vector_search(
                embedding_vector=np.array(self.embedding_function(doc["content"])).tolist(),
                n_results=1,
                collection=collection,
                index_name=index_name,
            )
            if query_result and query_result[0][0]["_id"] == doc["id"]:
                return
            sleep(_DELAY)

        raise TimeoutError(f"Document {self.index_name} is not ready!")

    def _get_embedding_size(self):
        return len(self.embedding_function(_SAMPLE_SENTENCE)[0])

    def list_collections(self):
        """
        List the collections in the vector database.

        Returns:
            List[str] | The list of collections.
        """
        return self.db.list_collection_names()

    def create_collection(
        self,
        collection_name: str,
        overwrite: bool = False,
        get_or_create: bool = True,
    ) -> Collection:
        """
        Create a collection in the vector database and create a vector search index in the collection.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get or create the collection. Default is True
        """
        if overwrite:
            self.delete_collection(collection_name)

        if collection_name not in self.db.list_collection_names():
            # Create a new collection
            coll = self.db.create_collection(collection_name)
            self.create_index_if_not_exists(index_name=self.index_name, collection=coll)
            return coll

        if get_or_create:
            # The collection already exists, return it.
            coll = self.db[collection_name]
            self.create_index_if_not_exists(index_name=self.index_name, collection=coll)
            return coll
        else:
            # get_or_create is False and the collection already exists, raise an error.
            raise ValueError(f"Collection {collection_name} already exists.")

    def create_index_if_not_exists(self, index_name: str = "vector_index", collection: Collection = None) -> None:
        """
        Creates a vector search index on the specified collection in MongoDB.

        Args:
            MONGODB_INDEX (str, optional): The name of the vector search index to create. Defaults to "vector_search_index".
            collection (Collection, optional): The MongoDB collection to create the index on. Defaults to None.
        """
        if not self._is_index_ready(collection, index_name):
            self.create_vector_search_index(collection, index_name)

    def get_collection(self, collection_name: str = None) -> Collection:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Collection | The collection object.
        """
        if collection_name is None:
            if self.active_collection is None:
                raise ValueError("No collection is specified.")
            else:
                logger.debug(
                    f"No collection is specified. Using current active collection {self.active_collection.name}."
                )
        else:
            self.active_collection = self.db[collection_name]

        return self.active_collection

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.
        """
        for index in self.db[collection_name].list_search_indexes():
            self.db[collection_name].drop_search_index(index["name"])
            if self._wait_until_index_ready:
                self._wait_for_index(self.db[collection_name], index["name"], "delete")
        return self.db[collection_name].drop()

    def create_vector_search_index(
        self,
        collection: Collection,
        index_name: Union[str, None] = "vector_index",
        similarity: Literal["euclidean", "cosine", "dotProduct"] = "cosine",
    ) -> None:
        """Create a vector search index in the collection.

        Args:
            collection: An existing Collection in the Atlas Database.
            index_name: Vector Search Index name.
            similarity: Algorithm used for measuring vector similarity.
            kwargs: Additional keyword arguments.

        Returns:
            None
        """
        search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "numDimensions": self.dimensions,
                        "path": "embedding",
                        "similarity": similarity,
                    },
                ]
            },
            name=index_name,
            type="vectorSearch",
        )
        # Create the search index
        try:
            collection.create_search_index(model=search_index_model)
            if self._wait_until_index_ready:
                self._wait_for_index(collection, index_name, "create")
            logger.debug(f"Search index {index_name} created successfully.")
        except Exception as e:
            logger.error(
                f"Error creating search index: {e}. \n"
                f"Your client must be connected to an Atlas cluster. "
                f"You may have to manually create a Collection and Search Index "
                f"if you are on a free/shared cluster."
            )
            raise e

    def insert_docs(
        self,
        docs: List[Document],
        collection_name: str = None,
        upsert: bool = False,
        batch_size=DEFAULT_INSERT_BATCH_SIZE,
        **kwargs,
    ) -> None:
        """Insert Documents and Vector Embeddings into the collection of the vector database.

        For large numbers of Documents, insertion is performed in batches.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            batch_size: Number of documents to be inserted in each batch
        """
        if not docs:
            logger.info("No documents to insert.")
            return

        collection = self.get_collection(collection_name)
        if upsert:
            self.update_docs(docs, collection.name, upsert=True)
        else:
            # Sanity checking the first document
            if docs[0].get("content") is None:
                raise ValueError("The document content is required.")
            if docs[0].get("id") is None:
                raise ValueError("The document id is required.")

            input_ids = set()
            result_ids = set()
            id_batch = []
            text_batch = []
            metadata_batch = []
            size = 0
            i = 0
            for doc in docs:
                id = doc["id"]
                text = doc["content"]
                metadata = doc.get("metadata", {})
                id_batch.append(id)
                text_batch.append(text)
                metadata_batch.append(metadata)
                id_size = 1 if isinstance(id, int) else len(id)
                size += len(text) + len(metadata) + id_size
                if (i + 1) % batch_size == 0 or size >= 47_000_000:
                    result_ids.update(self._insert_batch(collection, text_batch, metadata_batch, id_batch))
                    input_ids.update(id_batch)
                    id_batch = []
                    text_batch = []
                    metadata_batch = []
                    size = 0
                i += 1
            if text_batch:
                result_ids.update(self._insert_batch(collection, text_batch, metadata_batch, id_batch))  # type: ignore
                input_ids.update(id_batch)

            if result_ids != input_ids:
                logger.warning(
                    "Possible data corruption. "
                    "input_ids not in result_ids: {in_diff}.\n"
                    "result_ids not in input_ids: {out_diff}".format(
                        in_diff=input_ids.difference(result_ids), out_diff=result_ids.difference(input_ids)
                    )
                )
            if self._wait_until_document_ready and docs:
                self._wait_for_document(collection, self.index_name, docs[-1])

    def _insert_batch(
        self, collection: Collection, texts: List[str], metadatas: List[Mapping[str, Any]], ids: List[ItemID]
    ) -> Set[ItemID]:
        """Compute embeddings for and insert a batch of Documents into the Collection.

        For performance reasons, we chose to call self.embedding_function just once,
        with the hopefully small tradeoff of having recreating Document dicts.

        Args:
            collection: MongoDB Collection
            texts: List of the main contents of each document
            metadatas: List of metadata mappings
            ids: List of ids. Note that these are stored as _id in Collection.

        Returns:
            List of ids inserted.
        """
        n_texts = len(texts)
        if n_texts == 0:
            return []
        # Embed and create the documents
        embeddings = self.embedding_function(texts).tolist()
        assert (
            len(embeddings) == n_texts
        ), f"The number of embeddings produced by self.embedding_function ({len(embeddings)} does not match the number of texts provided to it ({n_texts})."
        to_insert = [
            {"_id": i, "content": t, "metadata": m, "embedding": e}
            for i, t, m, e in zip(ids, texts, metadatas, embeddings)
        ]
        # insert the documents in MongoDB Atlas
        insert_result = collection.insert_many(to_insert)  # type: ignore
        return insert_result.inserted_ids  # TODO Remove this. Replace by log like update_docs

    def update_docs(self, docs: List[Document], collection_name: str = None, **kwargs: Any) -> None:
        """Update documents, including their embeddings, in the Collection.

        Optionally allow upsert as kwarg.

        Uses deepcopy to avoid changing docs.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Any | Use upsert=True` to insert documents whose ids are not present in collection.
        """

        n_docs = len(docs)
        logger.info(f"Preparing to embed and update {n_docs=}")
        # Compute the embeddings
        embeddings: list[list[float]] = self.embedding_function([doc["content"] for doc in docs]).tolist()
        # Prepare the updates
        all_updates = []
        for i in range(n_docs):
            doc = deepcopy(docs[i])
            doc["embedding"] = embeddings[i]
            doc["_id"] = doc.pop("id")

            all_updates.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=kwargs.get("upsert", False)))
        # Perform update in bulk
        collection = self.get_collection(collection_name)
        result = collection.bulk_write(all_updates)

        if self._wait_until_document_ready and docs:
            self._wait_for_document(collection, self.index_name, docs[-1])

        # Log a result summary
        logger.info(
            "Matched: %s, Modified: %s, Upserted: %s",
            result.matched_count,
            result.modified_count,
            result.upserted_count,
        )

    def delete_docs(self, ids: List[ItemID], collection_name: str = None, **kwargs):
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
        """
        collection = self.get_collection(collection_name)
        return collection.delete_many({"_id": {"$in": ids}})

    def get_docs_by_ids(
        self, ids: List[ItemID] = None, collection_name: str = None, include: List[str] = None, **kwargs
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include.
                If None, will include ["metadata", "content"], ids will always be included.
                Basically, use include to choose whether to include embedding and metadata
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        if include is None:
            include_fields = {"_id": 1, "content": 1, "metadata": 1}
        else:
            include_fields = {k: 1 for k in set(include).union({"_id"})}
        collection = self.get_collection(collection_name)
        if ids is not None:
            docs = collection.find({"_id": {"$in": ids}}, include_fields)
            # Return with _id field from Collection into id for Document
            return with_id_rename(docs)
        else:
            docs = collection.find({}, include_fields)
            # Return with _id field from Collection into id for Document
            return with_id_rename(docs)

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict | Additional keyword arguments. Ones of importance follow:
                oversampling_factor: int | This times n_results is 'ef' in the HNSW algorithm.
                It determines the number of nearest neighbor candidates to consider during the search phase.
                A higher value leads to more accuracy, but is slower. Default is 10

        Returns:
            QueryResults | For each query string, a list of nearest documents and their scores.
        """
        collection = self.get_collection(collection_name)
        # Trivial case of an empty collection
        if collection.count_documents({}) == 0:
            return []

        logger.debug(f"Using index: {self.index_name}")
        results = []
        for query_text in queries:
            # Compute embedding vector from semantic query
            logger.debug(f"Query: {query_text}")
            query_vector = np.array(self.embedding_function([query_text])).tolist()[0]
            # Find documents with similar vectors using the specified index
            query_result = _vector_search(
                query_vector,
                n_results,
                collection,
                self.index_name,
                distance_threshold,
                **kwargs,
                oversampling_factor=kwargs.get("oversampling_factor", 10),
            )
            # Change each _id key to id. with_id_rename, but with (doc, score) tuples
            results.append(
                [({**{k: v for k, v in d[0].items() if k != "_id"}, "id": d[0]["_id"]}, d[1]) for d in query_result]
            )
        return results


def _vector_search(
    embedding_vector: List[float],
    n_results: int,
    collection: Collection,
    index_name: str,
    distance_threshold: float = -1.0,
    oversampling_factor=10,
    include_embedding=False,
) -> List[Tuple[Dict, float]]:
    """Core $vectorSearch Aggregation pipeline.

    Args:
        embedding_vector: Embedding vector of semantic query
        n_results: Number of documents to return. Defaults to 4.
        collection: MongoDB Collection with vector index
        index_name: Name of the vector index
        distance_threshold: Only distance measures smaller than this will be returned.
            Don't filter with it if 1 < x < 0. Default is -1.
        oversampling_factor: int | This times n_results is 'ef' in the HNSW algorithm.
            It determines the number of nearest neighbor candidates to consider during the search phase.
            A higher value leads to more accuracy, but is slower. Default = 10

    Returns:
        List of tuples of length n_results from Collection.
        Each tuple contains a document dict and a score.
    """

    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "limit": n_results,
                "numCandidates": n_results * oversampling_factor,
                "queryVector": embedding_vector,
                "path": "embedding",
            }
        },
        {"$set": {"score": {"$meta": "vectorSearchScore"}}},
    ]
    if distance_threshold >= 0.0:
        similarity_threshold = 1.0 - distance_threshold
        pipeline.append({"$match": {"score": {"$gte": similarity_threshold}}})

    if not include_embedding:
        pipeline.append({"$project": {"embedding": 0}})

    logger.debug("pipeline: %s", pipeline)
    agg = collection.aggregate(pipeline)
    return [(doc, doc.pop("score")) for doc in agg]
