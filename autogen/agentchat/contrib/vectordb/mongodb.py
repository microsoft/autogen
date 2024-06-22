from typing import Callable, List, Literal

import numpy as np
from pymongo import MongoClient, errors
from pymongo.operations import SearchIndexModel
from sentence_transformers import SentenceTransformer

from .base import Document, ItemID, QueryResults, VectorDB
from .utils import get_logger

logger = get_logger(__name__)


class MongoDBAtlasVectorDB(VectorDB):
    """
    A Collection object for MongoDB.
    """

    def __init__(
        self,
        connection_string: str = "",
        database_name: str = "vector_db",
        embedding_function: Callable = SentenceTransformer("all-MiniLM-L6-v2").encode,
    ):
        """
        Initialize the vector database.

        Args:
            connection_string: str | The MongoDB connection string to connect to. Default is ''.
            database_name: str | The name of the database. Default is 'vector_db'.
            embedding_function: The embedding function used to generate the vector representation.
        """
        if embedding_function:
            self.embedding_function = embedding_function
        try:
            self.client = MongoClient(connection_string)
            self.client.admin.command("ping")
        except errors.ServerSelectionTimeoutError as err:
            raise ConnectionError("Could not connect to MongoDB server") from err

        self.db = self.client[database_name]
        self.active_collection = None
        # This will get the model dimension size by computing the embeddings dimensions
        sentences = [
            "The weather is lovely today in paradise.",
        ]
        embeddings = self.embedding_function(sentences)
        self.dimensions = len(embeddings[0])

    def list_collections(self):
        """
        List the collections in the vector database.

        Returns:
            List[str] | The list of collections.
        """
        try:
            return self.db.list_collection_names()
        except Exception as err:
            raise err

    def create_collection(
        self,
        collection_name: str,
        overwrite: bool = False,
        get_or_create: bool = True,
        index_name: str = "default_index",
        similarity: Literal["euclidean", "cosine", "dotProduct"] = "cosine",
    ):
        """
        Create a collection in the vector database and create a vector search index in the collection.

        Args:
            collection_name: str | The name of the collection.
            index_name: str | The name of the index.
            similarity: str | The similarity metric for the vector search index.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True
        """
        # if overwrite is False and get_or_create is False, raise a ValueError
        if not overwrite and not get_or_create:
            raise ValueError("If overwrite is False, get_or_create must be True.")
        # If overwrite is True and the collection already exists, drop the existing collection
        collection_names = self.db.list_collection_names()
        if overwrite and collection_name in collection_names:
            self.db.drop_collection(collection_name)
        # If get_or_create is True and the collection already exists, return the existing collection
        if get_or_create and collection_name in collection_names:
            return self.db[collection_name]
        # If get_or_create is False and the collection already exists, raise a ValueError
        if not get_or_create and collection_name in collection_names:
            raise ValueError(f"Collection {collection_name} already exists.")

        # Create a new collection
        collection = self.db.create_collection(collection_name)
        # Create a vector search index in the collection
        search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {"type": "vector", "numDimensions": self.dimensions, "path": "embedding", "similarity": similarity},
                ]
            },
            name=index_name,
            type="vectorSearch",
        )
        # Create the search index
        try:
            collection.create_search_index(model=search_index_model)
            return collection
        except Exception as e:
            logger.error(f"Error creating search index: {e}")
            raise e

    def get_collection(self, collection_name: str = None):
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
            if collection_name not in self.list_collections():
                raise ValueError(f"Collection {collection_name} does not exist.")
            if self.active_collection is None:
                self.active_collection = self.db[collection_name]
        return self.active_collection

    def delete_collection(self, collection_name: str):
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.
        """
        return self.db[collection_name].drop()

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False):
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
        """
        if not docs:
            return
        if docs[0].get("content") is None:
            raise ValueError("The document content is required.")
        if docs[0].get("id") is None:
            raise ValueError("The document id is required.")
        collection = self.get_collection(collection_name)
        for doc in docs:
            if "embedding" not in doc:
                doc["embedding"] = np.array(self.embedding_function([str(doc["content"])])).tolist()[0]
        if upsert:
            for doc in docs:
                return collection.replace_one({"id": doc["id"]}, doc, upsert=True)
        else:
            return collection.insert_many(docs)

    def update_docs(self, docs: List[Document], collection_name: str = None):
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.
        """
        return self.insert_docs(docs, collection_name, upsert=True)

    def delete_docs(self, ids: List[ItemID], collection_name: str = None):
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
        """
        collection = self.get_collection(collection_name)
        return collection.delete_many({"id": {"$in": ids}})

    def get_docs_by_ids(self, ids: List[ItemID] = None, collection_name: str = None):
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
        """
        results = []
        if ids is None:
            collection = self.get_collection(collection_name)
            results = list(collection.find({}, {"embedding": 0}))
        else:
            for id in ids:
                id = str(id)
            collection = self.get_collection(collection_name)
            results = list(collection.find({"id": {"$in": ids}}, {"embedding": 0}))
        return results

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        index_name: str = "default",
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
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        results = []
        for query_text in queries:
            query_vector = np.array(self.embedding_function([query_text])).tolist()[0]
            # Find documents with similar vectors using the specified index
            search_collection = self.get_collection(collection_name)
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "limit": n_results,
                        "numCandidates": n_results,
                        "queryVector": query_vector,
                        "path": "embedding",
                    }
                },
                {"$project": {"score": {"$meta": "vectorSearchScore"}}},
            ]
            if distance_threshold >= 0.00:
                similarity_threshold = 1 - distance_threshold
                pipeline.append({"$match": {"score": {"gte": similarity_threshold}}})

            # do a lookup on the same collection
            pipeline.append(
                {
                    "$lookup": {
                        "from": collection_name,
                        "localField": "_id",
                        "foreignField": "_id",
                        "as": "full_document_array",
                    }
                }
            )
            pipeline.append(
                {
                    "$addFields": {
                        "full_document": {
                            "$arrayElemAt": [
                                {
                                    "$map": {
                                        "input": "$full_document_array",
                                        "as": "doc",
                                        "in": {"id": "$$doc.id", "content": "$$doc.content"},
                                    }
                                },
                                0,
                            ]
                        }
                    }
                }
            )
            pipeline.append({"$project": {"full_document_array": 0, "embedding": 0}})
            tmp_results = []
            for doc in search_collection.aggregate(pipeline):
                tmp_results.append((doc["full_document"], 1 - doc["score"]))
            results.append(tmp_results)
        return results
