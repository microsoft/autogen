# packages/autogen-ext/tests/storage/test_chroma_db.py
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from autogen_ext.storage import AsyncChromaVectorDB, ChromaVectorDB
from autogen_ext.storage._base import Document
from chromadb.errors import ChromaError


# Fixture for the synchronous database instance with module-level scope
@pytest.fixture(scope="module")
def db() -> Generator[ChromaVectorDB, None, None]:
    db_instance = ChromaVectorDB(path=".db")
    yield db_instance
    # Teardown code if necessary
    db_instance.client.reset()  # Or any other cleanup if needed


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


# Fixture for the event loop (required by pytest-asyncio)
@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Fixture for the asynchronous database instance with module-level scope
@pytest_asyncio.fixture(scope="module")  # type: ignore
async def async_db() -> AsyncGenerator[AsyncChromaVectorDB, None]:
    # Provide an embedding function compatible with async context
    async def embedding_function(texts: list[str]) -> list[list[float]]:
        # Dummy embedding function; replace with actual implementation
        return [[0.0] * 384 for _ in texts]

    db_instance = AsyncChromaVectorDB(embedding_function=embedding_function)  # type: ignore
    yield db_instance
    await db_instance.client.reset()  # Or any other cleanup if needed


# Fixture for the asynchronous collection name
@pytest.fixture(scope="module")
def async_collection_name() -> str:
    return "test_async_collection"


@pytest.mark.asyncio
async def test_async_create_collection(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    collection = await async_db.create_collection(async_collection_name, overwrite=True, get_or_create=True)
    assert collection.name == async_collection_name


@pytest.mark.asyncio
async def test_async_delete_collection(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    await async_db.delete_collection(async_collection_name)
    with pytest.raises((ValueError, ChromaError)):
        await async_db.get_collection(async_collection_name)


@pytest.mark.asyncio
async def test_async_more_create_collection(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    collection = await async_db.create_collection(async_collection_name, overwrite=False, get_or_create=False)
    assert collection.name == async_collection_name
    with pytest.raises((ValueError, ChromaError)):
        await async_db.create_collection(async_collection_name, overwrite=False, get_or_create=False)
    collection = await async_db.create_collection(async_collection_name, overwrite=True, get_or_create=False)
    assert collection.name == async_collection_name
    collection = await async_db.create_collection(async_collection_name, overwrite=False, get_or_create=True)
    assert collection.name == async_collection_name


@pytest.mark.asyncio
async def test_async_get_collection(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    collection = await async_db.get_collection(async_collection_name)
    assert collection.name == async_collection_name


@pytest.mark.asyncio
async def test_async_insert_docs(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    docs = [Document(content="doc1", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
    await async_db.insert_docs(docs, async_collection_name, upsert=False)
    collection = await async_db.get_collection(async_collection_name)
    res = await collection.get(["1", "2"])
    assert res["documents"] == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_async_update_docs(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    docs = [Document(content="doc11", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
    await async_db.update_docs(docs, async_collection_name)
    collection = await async_db.get_collection(async_collection_name)
    res = await collection.get(["1", "2"])
    assert res["documents"] == ["doc11", "doc2"]


@pytest.mark.asyncio
async def test_async_delete_docs(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    ids = ["1"]
    await async_db.delete_docs(ids, async_collection_name)
    collection = await async_db.get_collection(async_collection_name)
    res = await collection.get(ids)
    assert res["documents"] == []


@pytest.mark.asyncio
async def test_async_retrieve_docs(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    queries = ["doc2", "doc3"]
    res = await async_db.retrieve_docs(queries, async_collection_name)
    assert [[r[0].id for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = await async_db.retrieve_docs(queries, async_collection_name, distance_threshold=0.1)
    assert [[r[0].id for r in rr] for rr in res] == [["2"], ["3"]]


@pytest.mark.asyncio
async def test_async_get_docs_by_ids(async_db: AsyncChromaVectorDB, async_collection_name: str) -> None:
    res = await async_db.get_docs_by_ids(["1", "2"], async_collection_name)
    assert [r.id for r in res] == ["2"]
    res = await async_db.get_docs_by_ids(collection_name=async_collection_name)
    assert [r.id for r in res] == ["2", "3"]
