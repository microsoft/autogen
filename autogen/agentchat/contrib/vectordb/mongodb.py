from pymongo import MongoClient, errors
from typing import List
import re

from .base import QueryResults, VectorDB, Document, ItemID


class MongoDBVectorDB(VectorDB):
    """
    A vector database that uses MongoDB as the backend.
    """

    def __init__(self, connection_string: str = None, database_name: str = 'vector_db'):
        """
        Initialize the vector database.

        Args:
            host: str | The host to connect to. Default is 'localhost'.
            port: int | The port to connect to. Default is 27017.
            database_name: str | The name of the database. Default is 'vector_db'.
        """
        try:
            self.client = MongoClient(connection_string)
            self.client.server_info()
        except errors.ServerSelectionTimeoutError as err:
            # print error and handle exceptions
            print ("pymongo ERROR:", err)
            raise ConnectionError("Could not connect to MongoDB server")

        self.db = self.client[database_name]
        self.active_collection = None

    def is_valid_collection_name(self,name):
        """
        Checks if the collection name follows allowed characters and patterns.
      
        Args:
            name: str | The name of the collection.
      
        Returns:
            bool | True if the name is valid, False otherwise.
        """
        pattern = r"^[a-zA-Z0-9_\.]+$"  # Allows letters, numbers, underscores, and dots
        return bool(re.match(pattern, name))
    def create_collection(self, collection_name: str, overwrite: bool = False, get_or_create: bool = True):
          """
          Create a collection in the vector database.
        
          Args:
              collection_name: str | The name of the collection.
              overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
              get_or_create: bool | Whether to get the collection if it exists. Default is True.
          """
          if not self.is_valid_collection_name(collection_name):
            raise ValueError("Invalid collection name. Allowed characters: letters, numbers, underscores, and dots.")
        
          if overwrite and collection_name in self.db.list_collection_names():
            self.db[collection_name].drop()
          self.active_collection = self.db[collection_name]

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
        self.db[collection_name].drop()

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False):
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
        """
        collection = self.get_collection(collection_name)
        for doc in docs:
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
        self.insert_docs(docs, collection_name, upsert=True)

    def delete_docs(self, ids: List[ItemID], collection_name: str = None):
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
        """
        collection = self.get_collection(collection_name)
        for doc_id in ids:
            collection.delete_one({'id': doc_id})
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
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        return "TODO: Implement retrieve_docs function"
    def get_docs_by_ids(self, ids: List[ItemID] = None, collection_name: str = None):
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
        """
        collection = self.get_collection(collection_name)
        if ids is None:
            return list(collection.find())
        else:
            return list(collection.find({'id': {'$in': ids}}))

    def test(self):
        """
        Test the MongoDB connection and basic operations.
        """
        try:
            # Test connection
            self.client.server_info()

            # Test collection creation
            self.create_collection('test_collection', overwrite=True)

            # Test document insertion
            self.insert_docs([{'id': '1', 'content': 'test document'}], 'test_collection')

            # Test document retrieval
            docs = self.get_docs_by_ids(['1'], 'test_collection')
            assert len(docs) == 1 and docs[0]['id'] == '1'

            # Test document deletion
            self.delete_docs(['1'], 'test_collection')
            docs = self.get_docs_by_ids(['1'], 'test_collection')
            assert len(docs) == 0

            print("All tests passed.")
        except Exception as e:
            print("Test failed:", e)

# Test data
test_mdb_uri = ""
test_db_name = ""
test_collection_name = ""
test_documents = [{"id": "1", "content": "test document 1"}, {"id": "2", "content": "test document 2"}]

def test_mongodb_vector_db():
  """
  Tests the MongoDBVectorDB class functionality.
  """
  try:
    # Create a temporary MongoDB client and database for testing
    client = MongoClient(test_mdb_uri)
    db = client[test_db_name]

    # Create an instance of MongoDBVectorDB
    vector_db = MongoDBVectorDB(connection_string=test_mdb_uri, database_name=test_db_name)
    # Test collection creation with valid and invalid names
    vector_db.create_collection(test_collection_name)
    try:
      vector_db.create_collection("invalid_name!")  # Should raise an error
      assert False, "Invalid collection name creation not detected"
    except ValueError:
      pass  # Expected error for invalid name

    # Test document insertion and retrieval
    print(
        vector_db.insert_docs(test_documents, test_collection_name)
    )# insert works

    retrieved_docs = vector_db.get_docs_by_ids(collection_name=test_collection_name)
    assert len(retrieved_docs) == 2 and retrieved_docs == test_documents
    # get docs works
    # HOWEVER -- this test FAILS... AND NO VECTORS YET!
    # Test document deletion
    vector_db.delete_docs([doc["id"] for doc in test_documents], test_collection_name)
    retrieved_docs = vector_db.get_docs_by_ids(collection_name=test_collection_name)
    assert len(retrieved_docs) == 0

    print("All MongoDBVectorDB tests passed!")
  except Exception as e:
    print("Test failed:", e)
  finally:
    # Cleanup: Drop the temporary database
    db.drop()
    client.close()

test_mongodb_vector_db()