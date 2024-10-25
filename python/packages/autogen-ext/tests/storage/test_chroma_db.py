from typing import Generator

import pytest
from autogen_ext.storage import ChromaVectorDB
from autogen_ext.storage._base import Document
from chromadb.config import Settings
from chromadb.errors import ChromaError


# Fixture for the synchronous database instance with module-level scope
@pytest.fixture(scope="module")
def db() -> Generator[ChromaVectorDB, None, None]:
    db_instance = ChromaVectorDB(path=".db", settings=Settings(allow_reset=True))
    yield db_instance
    # Teardown code
    db_instance.client.reset()


# Fixture for the collection name
@pytest.fixture(scope="module")
def collection_name() -> str:
    return "test_collection"


def test_create_collection(db: ChromaVectorDB, collection_name: str) -> None:
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name


def test_delete_collection(db: ChromaVectorDB, collection_name: str) -> None:
    db.delete_collection(collection_name)
    with pytest.raises((ValueError, ChromaError)):
        db.get_collection(collection_name)


def test_more_create_collection(db: ChromaVectorDB, collection_name: str) -> None:
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=False)
    assert collection.name == collection_name
    with pytest.raises((ValueError, ChromaError)):
        db.create_collection(collection_name, overwrite=False, get_or_create=False)
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=False)
    assert collection.name == collection_name
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=True)
    assert collection.name == collection_name


def test_get_collection(db: ChromaVectorDB, collection_name: str) -> None:
    collection = db.get_collection(collection_name)
    assert collection.name == collection_name


def test_insert_docs(db: ChromaVectorDB, collection_name: str) -> None:
    docs = [Document(content="doc1", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc1", "doc2"]


def test_update_docs(db: ChromaVectorDB, collection_name: str) -> None:
    docs = [Document(content="doc11", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
    db.update_docs(docs, collection_name)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc11", "doc2"]


def test_delete_docs(db: ChromaVectorDB, collection_name: str) -> None:
    ids = ["1"]
    db.delete_docs(ids, collection_name)
    res = db.get_collection(collection_name).get(ids)
    assert res["documents"] == []


def test_retrieve_docs(db: ChromaVectorDB, collection_name: str) -> None:
    queries = ["doc2", "doc3"]
    res = db.retrieve_docs(queries, collection_name)
    assert [[r[0].id for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(queries, collection_name, distance_threshold=0.1)
    assert [[r[0].id for r in rr] for rr in res] == [["2"], ["3"]]


def test_get_docs_by_ids(db: ChromaVectorDB, collection_name: str) -> None:
    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert [r.id for r in res] == ["2"]
    res = db.get_docs_by_ids(collection_name=collection_name)
    assert [r.id for r in res] == ["2", "3"]
