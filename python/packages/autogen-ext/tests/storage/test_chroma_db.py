from pathlib import Path
from typing import Generator

import pytest
from autogen_ext.storage import ChromaVectorDB
from autogen_ext.storage._base import Document
from chromadb import Collection
from chromadb.config import Settings
from chromadb.errors import ChromaError


# Fixture for the synchronous database instance with function-level scope
@pytest.fixture(scope="function")
def db(tmp_path: Path) -> Generator[ChromaVectorDB, None, None]:
    db_path = tmp_path / "test_db"
    db_instance = ChromaVectorDB(path=str(db_path), settings=Settings(allow_reset=True))
    yield db_instance
    # Teardown code
    db_instance.client.reset()


# Fixture for unique collection names per test
@pytest.fixture(scope="function")
def collection_name(request: pytest.FixtureRequest) -> str:
    return f"test_collection_{request.node.name}"  # type: ignore


# Fixture to create and delete the collection around each test
@pytest.fixture(scope="function")
def collection(db: ChromaVectorDB, collection_name: str) -> Generator[Collection, None, None]:
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    yield collection
    db.delete_collection(collection_name)


def test_create_collection(db: ChromaVectorDB, collection_name: str) -> None:
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name


def test_delete_collection(db: ChromaVectorDB, collection_name: str) -> None:
    # Create the collection first
    db.create_collection(collection_name, overwrite=True, get_or_create=True)
    db.delete_collection(collection_name)
    with pytest.raises((ValueError, ChromaError)):
        db.get_collection(collection_name)


def test_more_create_collection(db: ChromaVectorDB, collection_name: str) -> None:
    # Ensure the collection is deleted at the start
    try:
        db.delete_collection(collection_name)
    except (ValueError, ChromaError):
        pass

    collection = db.create_collection(collection_name, overwrite=False, get_or_create=False)
    assert collection.name == collection_name
    with pytest.raises((ValueError, ChromaError)):
        db.create_collection(collection_name, overwrite=False, get_or_create=False)
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=False)
    assert collection.name == collection_name
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=True)
    assert collection.name == collection_name


def test_get_collection(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    retrieved_collection = db.get_collection(collection_name)
    assert retrieved_collection.name == collection_name


def test_insert_docs(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    docs = [
        Document(content="doc1", id="1"),
        Document(content="doc2", id="2"),
        Document(content="doc3", id="3"),
    ]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc1", "doc2"]


def test_update_docs(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    # Insert initial docs
    initial_docs = [
        Document(content="doc1", id="1"),
        Document(content="doc2", id="2"),
    ]
    db.insert_docs(initial_docs, collection_name, upsert=False)

    # Now update
    updated_docs = [
        Document(content="doc11", id="1"),
        Document(content="doc2", id="2"),
        Document(content="doc3", id="3"),
    ]
    db.update_docs(updated_docs, collection_name)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc11", "doc2"]


def test_delete_docs(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    # Insert initial docs
    initial_docs = [
        Document(content="doc1", id="1"),
        Document(content="doc2", id="2"),
    ]
    db.insert_docs(initial_docs, collection_name, upsert=False)

    ids = ["1"]
    db.delete_docs(ids, collection_name)
    res = db.get_collection(collection_name).get(ids)
    assert res["documents"] == []


def test_retrieve_docs(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    # Insert initial docs
    initial_docs = [
        Document(content="doc2", id="2"),
        Document(content="doc3", id="3"),
    ]
    db.insert_docs(initial_docs, collection_name, upsert=False)

    queries = ["doc2", "doc3"]
    res = db.retrieve_docs(queries, collection_name)
    assert [[r[0].id for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(queries, collection_name, distance_threshold=0.1)
    assert [[r[0].id for r in rr] for rr in res] == [["2"], ["3"]]


def test_get_docs_by_ids(db: ChromaVectorDB, collection_name: str, collection: Collection) -> None:
    # Insert initial docs
    initial_docs = [
        Document(content="doc2", id="2"),
        Document(content="doc3", id="3"),
    ]
    db.insert_docs(initial_docs, collection_name, upsert=False)

    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert [r.id for r in res] == ["2"]
    res = db.get_docs_by_ids(collection_name=collection_name)
    assert [r.id for r in res] == ["2", "3"]
