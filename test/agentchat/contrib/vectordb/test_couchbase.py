import logging
import os
import random
from time import monotonic, sleep
from typing import List

import pytest

from autogen.agentchat.contrib.vectordb.base import Document

try:
    from couchbase.cluster import Cluster, ClusterOptions
    from couchbase.auth import PasswordAuthenticator
    import sentence_transformers

    from autogen.agentchat.contrib.vectordb.couchbase import CouchbaseVectorDB
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning(
        f"skipping {__name__}. It requires one to pip install couchbase or the extra [retrievechat-couchbase]")
    pytest.skip(allow_module_level=True)

logger = logging.getLogger(__name__)

COUCHBASE_HOST = os.environ.get("CB_CONN_STR", "couchbase://localhost")
COUCHBASE_USERNAME = os.environ.get("CB_USERNAME", "Administrator")
COUCHBASE_PASSWORD = os.environ.get("CB_PASSWORD", "password")
COUCHBASE_BUCKET = os.environ.get("CB_BUCKET", "autogen_test_bucket")
COUCHBASE_SCOPE = os.environ.get("CB_SCOPE", "_default")
COUCHBASE_COLLECTION = os.environ.get("CB_COLLECTION", "autogen_test_vectorstore")
COUCHBASE_INDEX = os.environ.get("CB_INDEX_NAME", "vector_index")

RETRIES = 10
DELAY = 2
TIMEOUT = 120.0


def _wait_for_predicate(predicate, err, timeout=TIMEOUT, interval=DELAY):
    start = monotonic()
    while not predicate():
        if monotonic() - start > TIMEOUT:
            raise TimeoutError(err)
        sleep(DELAY)


def _delete_search_indexes(cluster, bucket_name, scope_name, collection_name):
    search_index_mgr = cluster.search_indexes()
    for index in search_index_mgr.get_all_indexes():
        if index.name.startswith(f"{bucket_name}.{scope_name}.{collection_name}"):
            search_index_mgr.drop_index(index.name)


def _empty_collections_and_delete_indexes(cluster, bucket_name, scope_name, collections=None):
    bucket = cluster.bucket(bucket_name)
    scope = bucket.scope(scope_name)
    for collection_name in collections or scope.collections():
        _delete_search_indexes(cluster, bucket_name, scope_name, collection_name)
        scope.collection(collection_name).truncate()


@pytest.fixture
def db():
    cluster = Cluster(COUCHBASE_HOST, ClusterOptions(PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)))
    _empty_collections_and_delete_indexes(cluster, COUCHBASE_BUCKET, COUCHBASE_SCOPE)
    vectorstore = CouchbaseVectorDB(
        connection_string=COUCHBASE_HOST,
        username=COUCHBASE_USERNAME,
        password=COUCHBASE_PASSWORD,
        bucket_name=COUCHBASE_BUCKET,
        scope_name=COUCHBASE_SCOPE,
        index_name=COUCHBASE_INDEX,
    )
    yield vectorstore
    _empty_collections_and_delete_indexes(cluster, COUCHBASE_BUCKET, COUCHBASE_SCOPE)


@pytest.fixture
def example_documents() -> List[Document]:
    return [
        Document(id="1", content="Dogs are tough.", metadata={"a": 1}),
        Document(id="2", content="Cats have fluff.", metadata={"b": 1}),
        Document(id="3", content="What is a sandwich?", metadata={"c": 1}),
        Document(id="4", content="A sandwich makes a great lunch.", metadata={"d": 1, "e": 2}),
    ]


@pytest.fixture
def db_with_indexed_clxn(collection_name):
    cluster = Cluster(COUCHBASE_HOST, ClusterOptions(PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)))
    _empty_collections_and_delete_indexes(cluster, COUCHBASE_BUCKET, COUCHBASE_SCOPE, [collection_name])
    vectorstore = CouchbaseVectorDB(
        connection_string=COUCHBASE_HOST,
        username=COUCHBASE_USERNAME,
        password=COUCHBASE_PASSWORD,
        bucket_name=COUCHBASE_BUCKET,
        scope_name=COUCHBASE_SCOPE,
        collection_name=collection_name,
        index_name=COUCHBASE_INDEX,
    )
    yield vectorstore, vectorstore.collection
    _empty_collections_and_delete_indexes(cluster, COUCHBASE_BUCKET, COUCHBASE_SCOPE, [collection_name])


_COLLECTION_NAMING_CACHE = []


@pytest.fixture
def collection_name():
    collection_id = random.randint(0, 100)
    while collection_id in _COLLECTION_NAMING_CACHE:
        collection_id = random.randint(0, 100)
    _COLLECTION_NAMING_CACHE.append(collection_id)
    return f"{COUCHBASE_COLLECTION}_{collection_id}"


def test_create_collection(db, collection_name):
    collection_case_1 = db.create_collection(collection_name=collection_name)
    assert collection_case_1.name == collection_name

    collection_case_2 = db.create_collection(collection_name=collection_name, overwrite=True)
    assert collection_case_2.name == collection_name

    collection_case_3 = db.create_collection(collection_name=collection_name)
    assert collection_case_3.name == collection_name

    with pytest.raises(ValueError):
        db.create_collection(collection_name=collection_name, overwrite=False, get_or_create=False)


def test_get_collection(db, collection_name):
    with pytest.raises(ValueError):
        db.get_collection()

    collection_created = db.create_collection(collection_name)
    assert collection_created.name == collection_name

    collection_got = db.get_collection(collection_name)
    assert collection_got.name == collection_created.name
    assert collection_got.name == db.active_collection.name


def test_delete_collection(db, collection_name):

    db.delete_collection(collection_name)
    with pytest.raises(ValueError):
        db.scope.collection(collection_name)

    with pytest.raises(ValueError):
        db.get_collection(collection_name)


def test_insert_docs(db, collection_name, example_documents):
    with pytest.raises(ValueError) as exc:
        db.insert_docs(example_documents)
    assert "No collection is specified" in str(exc.value)

    db.insert_docs(example_documents, collection_name, upsert=True)

    db.delete_collection(collection_name)
    collection = db.create_collection(collection_name)

    db.insert_docs(example_documents, collection_name=collection_name)
    found_docs = collection.get_multi([doc["id"] for doc in example_documents]).results
    assert len(found_docs) == len(example_documents)
    assert all([set(found_docs[doc_id].content_as[dict].keys()) == {"content", "metadata", "embedding"} for doc_id in
                found_docs])
    assert set(found_docs.keys()) == {"1", "2", "3", "4"}
    assert len(found_docs["1"].content_as[dict]["embedding"]) == 384


def test_update_docs(db_with_indexed_clxn, example_documents):
    db, collection = db_with_indexed_clxn
    db.update_docs(example_documents, collection.name, upsert=True)
    assert set(example_documents[0].keys()) == {"id", "content", "metadata"}
    assert collection.count() == len(example_documents)
    found = list(collection.get_all())
    assert all([set(doc.keys()) == {"content", "metadata", "embedding"} for doc in found])
    assert all([isinstance(doc["embedding"][0], float) for doc in found])
    assert all([len(doc["embedding"]) == db.dimensions for doc in found])
    assert {doc["id"] for doc in found} == {1, "1", 2, "2"}

    updated_doc = Document(id=1, content="Cats are tough.", metadata={"a": 10})
    db.update_docs([updated_doc], collection.name)
    assert collection.get(1)["content"] == "Cats are tough."

    new_id = 3
    new_doc = Document(id=new_id, content="Cats are tough.")
    db.update_docs([new_doc], collection.name, upsert=True)
    assert collection.get(new_id)["content"] == "Cats are tough."

    new_id = 4
    new_doc = Document(id=new_id, content="That is NOT a sandwich?")
    db.update_docs([new_doc], collection.name)
    assert collection.get(new_id) is None


def test_delete_docs(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)
    db.delete_docs(ids=[1, "1"], collection_name=clxn.name)
    assert {2, "2"} == {doc["id"] for doc in clxn.get_all()}


def test_get_docs_by_ids(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)

    docs = db.get_docs_by_ids(ids=[2, "2"], collection_name=clxn.name)
    assert len(docs) == 2
    assert all([doc["id"] in [2, "2"] for doc in docs])
    assert set(docs[0].keys()) == {"id", "content", "metadata"}

    docs = db.get_docs_by_ids(ids=[2], include=["content"], collection_name=clxn.name)
    assert len(docs) == 1
    assert set(docs[0].keys()) == {"id", "content"}

    docs = db.get_docs_by_ids(ids=[], include=["content"], collection_name=clxn.name)
    assert len(docs) == 0

    docs = db.get_docs_by_ids(ids=None, include=["content"], collection_name=clxn.name)
    assert len(docs) == 4


def test_retrieve_docs_empty(db_with_indexed_clxn):
    db, clxn = db_with_indexed_clxn
    assert db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=2) == []


def test_retrieve_docs_populated_db_empty_query(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)
    results = db.retrieve_docs(queries=[], collection_name=clxn.name, n_results=2)
    assert results == []


def test_retrieve_docs(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)

    n_results = 2

    def results_ready():
        results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results)
        return len(results[0]) == n_results

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    results = db.retrieve_docs(queries=["Cats"], collection_name=clxn.name, n_results=n_results)
    assert {doc[0]["id"] for doc in results[0]} == {1, 2}
    assert all(["embedding" not in doc[0] for doc in results[0]])


def test_retrieve_docs_multiple_queries(db_with_indexed_clxn, example_documents):
    db, clxn = db_with_indexed_clxn
    db.insert_docs(example_documents, collection_name=clxn.name)
    n_results = 2

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
    db.insert_docs(example_documents, collection_name=clxn.name)

    n_results = 2
    queries = ["Cats"]

    def results_ready():
        results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=n_results)
        return len(results[0]) == n_results

    _wait_for_predicate(results_ready, f"Failed to retrieve docs after waiting {TIMEOUT} seconds after each.")

    results = db.retrieve_docs(queries=queries, collection_name=clxn.name, n_results=n_results, distance_threshold=0.3)
    assert len(results[0]) == 1
    assert all([doc[1] >= 0.7 for doc in results[0]])
