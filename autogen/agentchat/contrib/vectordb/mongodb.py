from pymongo import MongoClient, errors
from typing import Callable, List
from sentence_transformers import SentenceTransformer
from pymongo.operations import SearchIndexModel
import numpy as np
from .base import Document, ItemID, QueryResults, VectorDB

class MongoDBVectorDB(VectorDB):
    """
    A Collection object for MongoDB.
    """
    def __init__(self, connection_string: str = '', database_name: str = 'vector_db', embedding_function: Callable = None,):
        """
        Initialize the vector database.

        Args:
            connection_string: str | The MongoDB connection string to connect to. Default is ''.
            database_name: str | The name of the database. Default is 'vector_db'.
            embedding_function: The embedding function used to generate the vector representation.
        """
        if embedding_function:
            self.embedding_function = embedding_function
        else:
            self.embedding_function = SentenceTransformer("all-MiniLM-L6-v2").encode
        try:
            self.client = MongoClient(connection_string)
            self.client.admin.command('ping')
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

    def is_valid_index_name(self, name: str) -> bool:
        """
        Checks if an index name is valid.

        Args:
            name: The name of the index to validate.

        Returns:
            True if the name is valid, False otherwise.
        """
        # Allowed characters (letters, numbers, underscores, and hyphens)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        # Check if the name is empty or starts/ends with non-alphanumeric characters
        if not name or name[0] not in allowed_chars or name[-1] not in allowed_chars:
            return False
        # Check if the name contains any characters other than allowed ones
        return all(char in allowed_chars for char in name)

    def is_valid_collection_name(self, name: str) -> bool:
        """
        Checks if a collection name is valid for MongoDB.

        Args:
            name: The name of the collection to validate.

        Returns:
            True if the name is valid, False otherwise.
        """
        # Allowed characters (letters, numbers, underscores, dots, and dollar signs)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.$_")
        # Check if the name is empty or starts/ends with a special character
        if not name or name[0] not in allowed_chars or name[-1] not in allowed_chars:
            return False
        # Check if the name contains any characters other than allowed ones
        return all(char in allowed_chars for char in name)
    def create_collection(self, collection_name: str, index_name:str, similarity:str, overwrite: bool = False, get_or_create: bool = True):
        """
        Create a collection in the vector database and create a vector search index in the collection.

        Args:
            collection_name: str | The name of the collection.
            index_name: str | The name of the index.
            similarity: str | The similarity metric for the vector search index.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True
        """
        # Check if similarity is valid
        if similarity not in ["euclidean", "cosine", "dotProduct"]:
            raise ValueError("Invalid similarity. Allowed values: 'euclidean', 'cosine', 'dotProduct'.")
        # Check if the index name is valid
        if not self.is_valid_index_name(index_name):
            raise ValueError("Invalid index name: "+ index_name +". Allowed characters: letters, numbers, underscores, and hyphens.")
        # Check if the collection name is valid
        if not self.is_valid_collection_name(collection_name):
            raise ValueError("Invalid collection name. Allowed characters: letters, numbers, underscores, and dots.")
        
        # If overwrite is True and the collection already exists, drop the existing collection
        if overwrite and collection_name in self.db.list_collection_names():
            self.db.drop_collection(collection_name)
        # If get_or_create is True and the collection already exists, return the existing collection
        if get_or_create and collection_name in self.db.list_collection_names():
            return self.db[collection_name]
        # If get_or_create is False and the collection already exists, raise a ValueError
        if not get_or_create and collection_name in self.db.list_collection_names():
            raise ValueError(f"Collection {collection_name} already exists.")
        
        # Create a new collection
        collection = self.db.create_collection(collection_name)
        # Create a vector search index in the collection
        # Check for existing index with the same name
        existing_indexes = collection.index_information()
        if index_name in existing_indexes:
            # Log a warning or handle the situation based on your needs
            raise ValueError(f"Index '{index_name}' already exists.")
        else:
            # Create the search index if it doesn't exist
            search_index_model = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "numDimensions": self.dimensions,
                            "path": "embedding",
                            "similarity": similarity
                        },
                    ]
                },
                name=index_name,
                type="vectorSearch"
            )
            # Create the search index
            try:
                collection.create_search_index(model=search_index_model)
                return collection
            except Exception as e:
                print(f"Error creating search index: {e}")
                raise e
        
    def get_collection(self, collection_name: str = None):
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.
        """
        if collection_name is None:
            if self.active_collection is None:
                raise ValueError("No collection is specified.")
            else:
                return self.active_collection
        else:
            return self.db[collection_name]

    def delete_collection(self, collection_name: str):
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.
        """
        return self.db.drop_collection(collection_name)

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
                doc["embedding"] = np.array(self.embedding_function([
                    str(doc["content"])
                ])).tolist()[0]
            if upsert:
                return collection.replace_one({'id': doc['id']}, doc, upsert=True)
            else:
                return collection.insert_one(doc)

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
        collection.delete_many({'id': ids})
        return ids

    def get_docs_by_ids(self, ids: List[ItemID] = None, collection_name: str = None):
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
        """
        for id in ids:
            id = str(id)
        collection = self.get_collection(collection_name)
        if ids is None:
            return list(collection.find())
        else:
            return list(collection.find({'id': {'$in': ids}}))
    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        index_name: str = "default",
        n_results: int = 10, n_candidates: int = 10,
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
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        for query_text in queries:
            query_vector = np.array(self.embedding_function([query_text])).tolist()[0]
            # Find documents with similar vectors using the specified index
            search_collection = self.get_collection(collection_name)
            if n_results > n_candidates:
                raise ValueError("n_results must be less than or equal to n_candidates.")
            if n_candidates < 1:
                raise ValueError("n_candidates must be greater than or equal to 1.")
            if not self.is_valid_index_name(index_name):
                raise ValueError("Invalid index name.")
            if not self.is_valid_collection_name(collection_name):
                raise ValueError("Invalid collection name.")
            pipeline = [
                {"$vectorSearch": {
                    "index": index_name, 
                    "limit": n_results, 
                    "numCandidates": n_candidates, 
                    "queryVector": query_vector, 
                    "path":"embedding"
                }},
                {
               '$project': {
                        'score': {
                            '$meta': 'vectorSearchScore'
                        }
                    }
                }]
            if distance_threshold >= 0:
                pipeline.append({"$match": {"score": {"$lte": distance_threshold}}})
            
            results = list(search_collection.aggregate(pipeline))
            return results
    
    
