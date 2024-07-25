import logging
import os
import random
from time import monotonic, sleep
from typing import List

import pytest

from autogen.agentchat.contrib.vectordb.base import Document

try:
    import pymongo
    import sentence_transformers

    from autogen.agentchat.contrib.vectordb.mongodb import MongoDBAtlasVectorDB
except ImportError:
    # To display warning in pyproject.toml [tool.pytest.ini_options] set log_cli = true
    logger = logging.getLogger(__name__)
    logger.warning(f"skipping {__name__}. It requires one to pip install pymongo or the extra [retrievechat-mongodb]")
    pytest.skip(allow_module_level=True)

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/?directConnection=true")
MONGODB_DATABASE = os.environ.get("DATABASE", "autogen_test_db")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION", "autogen_test_vectorstore")
MONGODB_INDEX = os.environ.get("MONGODB_INDEX", "vector_index")

RETRIES = 10
DELAY = 2
TIMEOUT = 120.0


def _wait_for_predicate(predicate, err, timeout=TIMEOUT, interval=DELAY):
    """Generic to block until the predicate returns true

    Args:
        predicate (Callable[, bool]): A function that returns a boolean value
        err (str): Error message to raise if nothing occurs
        timeout (float, optional): Length of time to wait for predicate. Defaults to TIMEOUT.
        interval (float, optional): Interval to check predicate. Defaults to DELAY.

    Raises:
        TimeoutError: _description_
    """
    start = monotonic()
    while not predicate():
        if monotonic() - start > TIMEOUT:
            raise TimeoutError(err)
        sleep(DELAY)


def _delete_search_indexes(collection: Collection, wait=True):
    """Deletes all indexes in a collection

    Args:
        collection (pymongo.Collection): MongoDB Collection Abstraction
    """
    for index in collection.list_search_indexes():
        try:
            collection.drop_search_index(index["name"])
        except OperationFailure:
            # Delete already issued
            pass
    if wait:
        _wait_for_predicate(lambda: not list(collection.list_search_indexes()), "Not all collections deleted")


def _empty_collections_and_delete_indexes(database, collections=None, wait=True):
    """Empty all collections within the database and remove indexes

    Args:
        database (pymongo.Database): MongoDB Database Abstraction
    """
    for collection_name in collections or database.list_collection_names():
        _delete_search_indexes(database[collection_name], wait)
        database[collection_name].drop()


@pytest.fixture
def db():
    """VectorDB setup and teardown, including collections and search indexes"""
    database = MongoClient(MONGODB_URI)[MONGODB_DATABASE]
    _empty_collections_and_delete_indexes(database)
    vectorstore = MongoDBAtlasVectorDB(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DATABASE,
        wait_until_index_ready=TIMEOUT,
        overwrite=True,
    )
    yield vectorstore
    _empty_collections_and_delete_indexes(database)


@pytest.fixture
def example_documents() -> List[Document]:
    """Note mix of integers and strings as ids"""
    return [
        Document(id=1, content="Dogs are tough.", metadata={"a": 1}),
        Document(id=2, content="Cats have fluff.", metadata={"b": 1}),
        Document(id="1", content="What is a sandwich?", metadata={"c": 1}),
        Document(id="2", content="A sandwich makes a great lunch.", metadata={"d": 1, "e": 2}),
    ]


@pytest.fixture
def db_with_indexed_clxn(collection_name):
    """VectorDB with a collection created immediately"""
    database = MongoClient(MONGODB_URI)[MONGODB_DATABASE]
    _empty_collections_and_delete_indexes(database, [collection_name], wait=True)
    vectorstore = MongoDBAtlasVectorDB(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DATABASE,
        wait_until_index_ready=TIMEOUT,
        collection_name=collection_name,
        overwrite=True,
    )
    yield vectorstore, vectorstore.db[collection_name]
    _empty_collections_and_delete_indexes(database, [collection_name])


_COLLECTION_NAMING_CACHE = []


@pytest.fixture
def collection_name():
    collection_id = random.randint(0, 100)
    while collection_id in _COLLECTION_NAMING_CACHE:
        collection_id = random.randint(0, 100)
    _COLLECTION_NAMING_CACHE.append(collection_id)

    return f"{MONGODB_COLLECTION}_{collection_id}"


def test_create_collection(db, collection_name):
    """
    def create_collection(collection_name: str,
                        overwrite: bool = False) -> Collection
    Create a collection in the vector database.
    - Case 1. if the collection does not exist, create the collection.
    - Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
    - Case 3. the collection exists and overwrite is False return the existing collection.
    - Case 4. the collection exists and overwrite is False and get_or_create is False, raise a ValueError
    """
    collection_case_1 = db.create_collection(
        collection_name=collection_name,
    )
    assert collection_case_1.name == collection_name

    collection_case_2 = db.create_collection(
        collection_name=collection_name,
        overwrite=True,
    )
    assert collection_case_2.name == collection_name

    collection_case_3 = db.create_collection(
        collection_name=collection_name,
    )
    assert collection_case_3.name == collection_name

    with pytest.raises(ValueError):
        db.create_collection(collection_name=collection_name, overwrite=False, get_or_create=False)


def test_get_collection(db, collection_name):
    with pytest.raises(ValueError):
        db.get_collection()

    collection_created = db.create_collection(collection_name)
    assert isinstance(collection_created, Collection)
    assert collection_created.name == collection_name

    collection_got = db.get_collection(collection_name)
    assert collection_got.name == collection_created.name
    assert collection_got.name == db.active_collection.name


def test_delete_collection(db, collection_name):
    assert collection_name not in db.list_collections()
    collection = db.create_collection(collection_name)
    assert collection_name in db.list_collections()
    db.delete_collection(collection.name)
    assert collection_name not in db.list_collections()


def test_insert_docs(db, collection_name, example_documents):
    # Test that there's an active collection
    with pytest.raises(ValueError) as exc:
        db.insert_docs(example_documents)
    assert "No collection is specified" in str(exc.value)

    # Test upsert
    db.insert_docs(example_documents, collection_name, upsert=True)

    # Create a collection
    db.delete_collection(collection_name)
    collection = db.create_collection(collection_name)

    # Insert example documents
    db.insert_docs(example_documents, collection_name=collection_name)
    found = list(collection.find({}))
    assert len(found) == len(example_documents)
    # Check that documents have correct fields, including "_id" and "embedding" but not "id"
    assert all([set(doc.keys()) == {"_id", "content", "metadata", "embedding"} for doc in found])
    # Check ids
    assert {doc["_id"] for doc in found} == {1, "1", 2, "2"}
    # Check embedding lengths
    assert len(found[0]["embedding"]) == 384


def test_update_docs(db_with_indexed_clxn, example_documents):
    db, collection = db_with_indexed_clxn
    # Use update_docs to insert new documents
    db.update_docs(example_documents, collection.name, upsert=True)
    # Test that no changes were made to example_documents
    assert set(example_documents[0].keys()) == {"id", "content", "metadata"}
    assert collection.count_documents({}) == len(example_documents)
    found = list(collection.find({}))
    # Check that documents have correct fields, including "_id" and "embedding" but not "id"
    assert all([set(doc.keys()) == {"_id", "content", "metadata", "embedding"} for doc in found])
    assert all([isinstance(doc["embedding"][0], float) for doc in found])
    assert all([len(doc["embedding"]) == db.dimensions for doc in found])
    # Check ids
    assert {doc["_id"] for doc in found} == {1, "1", 2, "2"}

    # Update an *existing* Document
    updated_doc = Document(id=1, content="Cats are tough.", metadata={"a": 10})
    db.update_docs([updated_doc], collection.name)
    assert collection.find_one({"_id": 1})["content"] == "Cats are tough."

    # Upsert a *new* Document
    new_id = 3
    new_doc = Document(id=new_id, content="Cats are tough.")
    db.update_docs([new_doc], collection.name, upsert=True)
    assert collection.find_one({"_id": new_id})["content"] == "Cats are tough."

    # Attempting to use update to insert a new doc
    # *without* setting upsert set to True
    # is a no-op in MongoDB. # TODO Confirm behaviour and autogen's preference.
    new_id = 4
    new_doc = Document(id=new_id, content="That is NOT a sandwich?")
    db.update_docs([new_doc], collection.name)
    assert collection.find_one({"_id": new_id}) is None


def test_delete_docs(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)
    # Delete the 1s
    db.delete_docs(ids=[1, "1"], collection_name=clxn.name)
    # Confirm just the 2s remain
    assert {2, "2"} == {doc["_id"] for doc in clxn.find({})}


def test_get_docs_by_ids(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)

    # Test without setting "include" kwarg
    docs = db.get_docs_by_ids(ids=[2, "2"], collection_name=clxn.name)
    assert len(docs) == 2
    assert all([doc["id"] in [2, "2"] for doc in docs])
    assert set(docs[0].keys()) == {"id", "content", "metadata"}

    # Test with include
    docs = db.get_docs_by_ids(ids=[2], include=["content"], collection_name=clxn.name)
    assert len(docs) == 1
    assert set(docs[0].keys()) == {"id", "content"}

    # Test with empty ids list
    docs = db.get_docs_by_ids(ids=[], include=["content"], collection_name=clxn.name)
    assert len(docs) == 0

    # Test with empty ids list
    docs = db.get_docs_by_ids(ids=None, include=["content"], collection_name=clxn.name)
    assert len(docs) == 4


def test_retrieve_docs_empty(db_with_indexed_clxn):
    db, clxn = db_with_indexed_clxn
    assert db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=2) == []


def test_retrieve_docs_populated_db_empty_query(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)
    # Empty list of queries returns empty list of results
    results = db.retrieve_docs(queries=[], collection_name=clxn.name, n_results=2)
    assert results == []


def test_retrieve_docs(db_with_indexed_clxn, example_documents):
    """Begin testing Atlas Vector Search
    NOTE: Indexing may take some time, so we must be patient on the first query.
    We have the wait_until_index_ready flag to ensure index is created and ready
    Immediately adding documents and then querying is only standard for testing
    """
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)

    n_results = 2  # Number of closest docs to return

    def results_ready():
        results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results)
        return len(results[0]) == n_results

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results)
    assert {doc[0]["id"] for doc in results[0]} == {1, 2}
    assert all(["embedding" not in doc[0] for doc in results[0]])


def test_retrieve_docs_with_embedding(db_with_indexed_clxn, example_documents):
    """Begin testing Atlas Vector Search
    NOTE: Indexing may take some time, so we must be patient on the first query.
    We have the wait_until_index_ready flag to ensure index is created and ready
    Immediately adding documents and then querying is only standard for testing
    """
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)

    n_results = 2  # Number of closest docs to return

    def results_ready():
        results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results)
        return len(results[0]) == n_results

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results, include_embedding=True)
    assert {doc[0]["id"] for doc in results[0]} == {1, 2}
    assert all(["embedding" in doc[0] for doc in results[0]])


def test_retrieve_docs_multiple_queries(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)
    n_results = 2  # Number of closest docs to return

    queries = ["Some good pets", "What kind of Sandwich?"]

    def results_ready():
        results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=n_results)
        return all([len(res) == n_results for res in results])

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=2)

    assert len(results) == len(queries)
    assert all([len(res) == n_results for res in results])
    assert {doc[0]["id"] for doc in results[0]} == {1, 2}
    assert {doc[0]["id"] for doc in results[1]} == {"1", "2"}


def test_retrieve_docs_with_threshold(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    # Insert example documents
    db.insert_docs(example_documents, collection_name=clxn.name)

    n_results = 2  # Number of closest docs to return
    queries = ["Cats"]

    def results_ready():
        results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=n_results)
        return len(results[0]) == n_results

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    # Distance Threshold of .3 means that the score must be .7 or greater
    # only one result should be that value
    results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=n_results, distance_threshold=0.3)
    assert len(results[0]) == 1
    assert all([doc[1] >= 0.7 for doc in results[0]])


def test_wait_until_document_ready(collection_name, example_documents):
    database = MongoClient(MONGODB_URI)[MONGODB_DATABASE]
    _empty_collections_and_delete_indexes(database, [collection_name], wait=True)
    try:
        vectorstore = MongoDBAtlasVectorDB(
            connection_string=MONGODB_URI,
            database_name=MONGODB_DATABASE,
            wait_until_index_ready=TIMEOUT,
            collection_name=collection_name,
            overwrite=True,
            wait_until_document_ready=TIMEOUT,
        )
        vectorstore.insert_docs(example_documents)
        assert vectorstore.retrieve_docs(queries=["Cats"], n_results=4)
    finally:
        _empty_collections_and_delete_indexes(database, [collection_name])
