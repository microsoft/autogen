import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
    import chromadb
    import sentence_transformers
    from autogen.agentchat.contrib.rag.chromadb import (
        ChromaVectorDB,
        Document,
        Query,
    )
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
def test_chromadb():
    # test create collection
    db = ChromaVectorDB(".db")
    collection_name = "test_collection"
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test_delete_collection
    db.delete_collection(collection_name)
    pytest.raises(ValueError, db.get_collection, collection_name)

    # test more create collection
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=False)
    assert collection.name == collection_name
    pytest.raises(ValueError, db.create_collection, collection_name, overwrite=False, get_or_create=False)
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=False)
    assert collection.name == collection_name
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=True)
    assert collection.name == collection_name

    # test_get_collection
    collection = db.get_collection(collection_name)
    assert collection.name == collection_name

    # test_insert_docs
    docs = [Document(content="doc1", id=1), Document(content="doc2", id=2), Document(content="doc3", id=3)]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_docs_by_ids(["1", "2"], collection_name, include=["documents"])
    assert res.texts == ["doc1", "doc2"]

    # test_update_docs
    docs = [Document(content="doc11", id=1), Document(content="doc2", id=2), Document(content="doc3", id=3)]
    db.update_docs(docs, collection_name)
    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert res.texts == ["doc11", "doc2"]

    # test_delete_docs
    ids = ["1"]
    collection_name = "test_collection"
    db.delete_docs(ids, collection_name)
    res = db.get_docs_by_ids(ids, collection_name)
    assert res.texts == []

    # test_retrieve_docs
    queries = [
        Query(text="doc2", k=2, include=None),
        Query(text="doc3", k=2, include=["distances", "documents"]),
    ]
    collection_name = "test_collection"
    res = db.retrieve_docs(queries, collection_name)
    assert res.ids == [["2", "3"], ["3", "2"]]


if __name__ == "__main__":
    test_chromadb()
